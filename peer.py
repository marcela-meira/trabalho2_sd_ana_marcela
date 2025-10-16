''' Para iniciar o servidor no terminal usar:
    python -m Pyro5.nameserver
'''

import Pyro5.api
import Pyro5.errors 
from Pyro5.server import Daemon
import threading
import time

RESOURCE_MAX_TIME=10
RESPONSE_MAX_TIME=20
HEARTBEAT_MAX_TIME=5

@Pyro5.api.expose
class Peer(object):
    def __init__(self,name):
        self.name=name
        self.state="RELEASED"
        self.resource_time=0
        self.timestamp=0
        self.my_request_timestamp = 0
        self.response_time=0
        self.request_queue = []
        self.lock = threading.RLock()
        self.peers_ativos = []
        self.contador_respostas=0
        self.ultimo_heartbeat = {}  # dicionário: {peer_name: timestamp}
    
    @Pyro5.api.oneway
    def usar_recurso(self):
        with self.lock:
            if self.state == "HELD" and self.resource_time and self.resource_time.is_alive():
                return  
            self.resource_time = threading.Timer(RESOURCE_MAX_TIME,self.liberar_recurso)
            self.resource_time.start()
    
    @Pyro5.api.oneway
    def remover_processo(self,peer_name):
        with self.lock:
            print(f"Removendo {peer_name} por inatividade ")
            if peer_name in self.peers_ativos:
                self.peers_ativos.remove(peer_name)
                if self.contador_respostas > 0:
                    self.contador_respostas-=1
            self.request_queue = [item for item in self.request_queue if item[0] != peer_name]
            
            #Verificar prioridade 
            if self.state == "WANTED" and self.contador_respostas == len(self.peers_ativos) and (not self.request_queue or self.my_request_timestamp < self.request_queue[0][1]):
                print(f"\nVocê pode acessar o recurso")
                self.state="HELD"
                self.usar_recurso()

    def heartbeat(self):

        ns=Pyro5.api.locate_ns()
        while True:
            try:
                lista_peers = list(ns.list().keys())[1:]
            except Pyro5.errors.NamingError:
                print("Heartbeat: Perda de conexão com o Servidor de Nomes.")
                time.sleep(HEARTBEAT_MAX_TIME)
                continue

            for peer_name in lista_peers:
                if peer_name==self.name:
                    continue        
                uri = ns.lookup(peer_name)
                peer_proxy = Pyro5.api.Proxy(uri)
                peer_proxy.receber_heartbeats(self.name)
                # print(f"Heartbeat enviado para {peer_name}")
                
            
            time.sleep(HEARTBEAT_MAX_TIME / 2)

    def solicitar_recurso(self):
        with self.lock:
            self.state="WANTED"
            self.my_request_timestamp=time.time()
            self.contador_respostas=0

        print(f"I want to enter the critical section and access resource")
        
        try:
            ns = Pyro5.api.locate_ns()
            lista_peers = list(ns.list().keys())[1:]
        except Pyro5.errors.NamingError:
            print("Solicitar Recurso: Não foi possível conectar ao Servidor de Nomes.")
            self.state = "RELEASED" 
            return

        for peer_name in lista_peers:
            if peer_name==self.name:
                continue
            
            try:
                uri=ns.lookup(peer_name)
                peer=Pyro5.api.Proxy(uri)
                with self.lock:
                    if peer_name not in self.peers_ativos:
                        self.peers_ativos.append(peer_name)

                print(f"Solicitando recurso para {peer_name}")
                self.response_time = threading.Timer(RESPONSE_MAX_TIME,self.remover_processo, args=[peer_name])
                self.response_time.start()

                resposta=peer.receber_pedido(self.name, self.my_request_timestamp)
                
                if resposta==True:
                    self.contador_respostas+=1
                    self.response_time.cancel()
                elif resposta==False:
                    self.response_time.cancel()
                    print(f"Você está na fila para acessar o recurso")
                
                if peer not in self.peers_ativos:
                    self.response_time.cancel()

            except (Pyro5.errors.CommunicationError, Pyro5.errors.NamingError) as e:
                print(f"Falha ao solicitar recurso para {peer_name}: {e}")
                self.response_time.cancel()
                self.remover_processo(peer_name)
                continue

        if self.contador_respostas == len(self.peers_ativos) and (not self.request_queue or self.my_request_timestamp < self.request_queue[0][1]):
            print(f"\nVocê pode acessar o recurso")
            self.state="HELD"
            self.usar_recurso()

    def receber_pedido(self, requester_name, request_timestamp):
        with self.lock:
            print(f"Solicitação recebida de {requester_name}")
            
            tempo_atual = time.time()
            ultimo_hb = self.ultimo_heartbeat.get(requester_name, 0)
            if tempo_atual - ultimo_hb > HEARTBEAT_MAX_TIME:
                print(f"{requester_name} está inativo, removendo...")
                self.remover_processo(requester_name)
                return False
            
            if (self.state=="WANTED" and self.my_request_timestamp < request_timestamp) or self.state=="HELD":
                self.request_queue.append((requester_name, request_timestamp))
                self.request_queue.sort(key=lambda x: (x[1], x[0]))
                print(f"\nSolicitação não aprovada para {requester_name}")
                return False
            else:
                print(f"\nSolicitação aprovada para {requester_name}")
                return True
            
    @Pyro5.api.oneway
    def liberar_recurso(self):
        with self.lock:
            if self.resource_time and self.resource_time.is_alive():
                self.resource_time.cancel()
                print(f"Timer de liberação automática cancelado")

            self.state="RELEASED"
            self.my_request_timestamp=0
            print(f"Recurso liberado.")
            self.request_queue = [item for item in self.request_queue if item[0] != self.name]
            queue_copy = list(self.request_queue)
            self.request_queue.clear()

        try:
            ns = Pyro5.api.locate_ns()
            for requester_name,_ in queue_copy:
                try:
                    uri = ns.lookup(requester_name)
                    requester_proxy = Pyro5.api.Proxy(uri)
                    print(f"Enviando permissão tardia para {requester_name}")
                    requester_proxy.receber_resposta(self.name)
                except (Pyro5.errors.CommunicationError, Pyro5.errors.NamingError):
                    print(f"Não foi possível enviar permissão para {requester_name}.")

        except Pyro5.errors.NamingError:
            print("Liberar Recurso: Não foi possível conectar ao Servidor de Nomes.")

    @Pyro5.api.oneway
    def receber_resposta(self, from_peer):
        with self.lock:
            print(f"Recebi liberação do recurso de {from_peer}")
            self.contador_respostas += 1
            #Verificar prioridade
            if self.state=="WANTED" and self.contador_respostas == len(self.peers_ativos) and (not self.request_queue or self.my_request_timestamp < self.request_queue[0][1]):
                print("\nVocê pode acessar o recurso (todas as respostas recebidas).")
                self.state = "HELD"
                self.usar_recurso()

    @Pyro5.api.oneway
    def receber_heartbeats(self,peer_name):
        with self.lock:
            self.ultimo_heartbeat[peer_name] = time.time()
            # print(f"Heartbeat recebido de {peer_name}")
    
    def monitorar_heartbeats(self):
        while True:
            with self.lock:
                copy=list(self.ultimo_heartbeat.items())
                tempo_atual = time.time()
                for peer_name, ultimo_hb in copy:
                    if tempo_atual - ultimo_hb > HEARTBEAT_MAX_TIME:
                        print(f"{peer_name} falhou (sem heartbeat há muito tempo)")
                        self.remover_processo(peer_name)
                        if peer_name in self.ultimo_heartbeat:
                            del self.ultimo_heartbeat[peer_name]
            time.sleep(5)


def main():
    name = input("What is your name? ").strip()
    daemon = Pyro5.server.Daemon()
    
    try:
        ns = Pyro5.api.locate_ns()
    except Pyro5.errors.NamingError:
        print("ERRO: Não foi possível localizar o Servidor de Nomes.")
        return

    peer=Peer(name)
    uri = daemon.register(peer)

    if name not in ns.list().keys():
        ns.register(name, uri)

    print("Ready.")
    threading.Thread(target=daemon.requestLoop, daemon=True).start()
    threading.Thread(target=peer.heartbeat, daemon=True).start()
    threading.Thread(target=peer.monitorar_heartbeats, daemon=True).start()

    while True:
        opcao = input(
            "\nSelecione a opção desejada:\n"
            "1. Solicitar recurso\n"
            "2. Listar peers ativos\n"
            "3. Liberar recurso\n"
            "4. Sair\n> "
        )
        if opcao == "1":
            print("Solicitar recurso\n")
            threading.Thread(target=peer.solicitar_recurso, daemon=True).start()
        elif opcao == "2":
            print("Listar peers ativos")
            print(ns.list())
        elif opcao == "3":
            print("Liberar recurso")
            peer.liberar_recurso()
        elif opcao == "4":
            print("Encerrando...")
            try:
                ns.remove(name)
            except Pyro5.errors.NamingError:
                print("Não foi possível remover o registro do Name Server.")
            break
        else:
            print("Opção inválida")
        
if __name__ == "__main__":
    main()
