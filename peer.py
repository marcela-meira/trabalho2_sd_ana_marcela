
''' Para iniciar o servidor no terminal usar:
    python -m Pyro5.nameserver
'''

import Pyro5.api
from Pyro5.server import Daemon
import threading
import time

RESOURCE_MAX_TIME=10  #ACHO Q DA P GENTE USAR ESSA MACRO P CONTROLAR O TEMPO DO RECURSO NA SEÇÃO CRÍTICA
RESPONSE_MAX_TIME=20

''' PROBLEMA ATUAL: quando solicita um recurso os peers ficam travados, nunca retornando ao menu principal
    Segundo Gemini: Em resumo, a lógica atual cria um ciclo de espera: o PeerB solicita, o PeerA recebe e aprova, 
    mas o PeerA fica travado esperando algo. Quando o PeerB libera o recurso, ele tenta "despertar" o PeerA chamando solicitar_recurso(),
    o que só agrava o impasse. A solução é que o PeerA receba uma notificação simples, permitindo que ele mesmo, de forma independente, continue seu processo.
    Acho que é aquela lógica que a gente tinha visto antes no chat de enviar um 'OK' e o próprio peer chamar seus métodos e não um peer chamar remotamente o 
    método para o outro.
'''

''' thread pra escutar heartbeat -> time.tempo_atual menos ultimo heartbeat se for maior que temporizador = nó falhou (fazer para todos os peers)
    alternativa: ter um threading timer que ativa a checagem acima de tempos em tempos
                marca quando recebe e de quem o heartbeat
                timer checa no tempo (temporizador + uns ms) se recebeu de todos
'''

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
        self.lock = threading.Lock()
        self.peers_ativos = []

    """def get_fortune(self, name):
        return "Hello, {0}. Here is your fortune message:\n" \
               "Tomorrow's lucky number is 12345678.".format(name)"""
    
    def usar_recurso(self):
        self.resource_time = threading.Timer(RESOURCE_MAX_TIME,self.liberar_recurso)
        self.resource_time.start()

    def remover_processo(self,peer_name):
        # O peer é removido da lista local de peers ativos
        print(f"Removendo {peer_name} por inatividade ")
        self.peers_ativos.remove(peer_name)

    def solicitar_recurso(self):
        with self.lock:
            self.state="WANTED"
            self.my_request_timestamp=time.time()
        print(f"I want to enter the critical section and access resource")
        # Mandar msg pra cada peer, exceto pra ele próprio
        contador=0
        ns = Pyro5.api.locate_ns()  
        
        self.peers_ativos.clear()

        for peer_name in list(ns.list().keys())[1:]:         
            if peer_name==self.name:
                continue
            uri=ns.lookup(peer_name)
            peer=Pyro5.api.Proxy(uri)

            self.peers_ativos.append(peer_name)

            print(f"Solicitando recurso para {peer_name}")
            self.response_time = threading.Timer(RESPONSE_MAX_TIME,self.remover_processo, args=[peer_name])
            self.response_time.start()

            resposta=peer.receber_pedido(self.name, self.my_request_timestamp)
            
            if resposta==True:
                contador+=1
                self.response_time.cancel()
            elif resposta==False:
               self.response_time.cancel()
               print(f"Você está na fila para acessar o recurso") 

        if contador == len(self.peers_ativos):
            print(f"\nVocê pode acessar o recurso")
            self.state="HELD"    
            self.usar_recurso()        
            return True

    # Colocar sleep para simular peer inativo
    
    #@Pyro5.api.oneway
    def receber_pedido(self, requester_name, request_timestamp):
        print(f"Solicitação recebida de {requester_name}")
        if (self.state=="WANTED" and self.my_request_timestamp < request_timestamp) or self.state=="HELD":
            self.request_queue.append((requester_name, request_timestamp))
            self.request_queue.sort(key=lambda x: (x[1], x[0]))
            print(f"\nSolicitação não aprovada para {requester_name}")
            return False
        else:
           print(f"\nSolicitação aprovada para {requester_name}")
           return True
        ## Simulação de peer inativo
        #time.sleep(30)
        
    def liberar_recurso(self):
        with self.lock:
            if self.resource_time and self.resource_time.is_alive():
                self.resource_time.cancel()
                print(f"Timer de liberação automática cancelado")

            self.state="RELEASED"
            self.my_request_timestamp=0
            print(f"Recurso liberado.")

        ns = Pyro5.api.locate_ns()  
        for requester_name,_ in self.request_queue:
            uri = ns.lookup(requester_name)
            requester_proxy = Pyro5.api.Proxy(uri)
            print(f"Enviando permissão tardia para {requester_name}")
            requester_proxy.solicitar_recurso()
        '''if self.request_queue :
            self.request_queue.clear()'''

def main():

    name = input("What is your name? ").strip()
    daemon = Pyro5.server.Daemon()         # make a Pyro daemon
    ns = Pyro5.api.locate_ns()             # find the name server

    peer=Peer(name)
    uri = daemon.register(peer) # register as a Pyro object

    if name not in ns.list().keys():          
        ns.register(name, uri)   # register the object with a name in the name server

    print("Ready.")
    threading.Thread(target=daemon.requestLoop, daemon=True).start()    # start the event loop of the server to wait for calls    

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
            print(ns.list())  # exemplo: mostra peers registrados
        elif opcao == "3":
            print("Liberar recurso")
            peer.liberar_recurso()
        elif opcao == "4":
            print("Encerrando...")
            ns.remove(name)   # remove peer do NameServer
            break
        else:
            print("Opção inválida")
        
if __name__ == "__main__":
    main()
    

    
