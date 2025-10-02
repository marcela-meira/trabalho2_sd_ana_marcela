
''' Para iniciar o servidor no terminal usar:
    python -m Pyro5.nameserver
'''

import Pyro5.api
from Pyro5.server import Daemon
import threading
import time

RESOURCE_MAX_TIME=10#ACHO Q DA P GENTE USAR ESSA MACRO P CONTROLAR O TEMPO DO RECURSO NA SEÇÃO CRÍTICA

@Pyro5.api.expose
class Peer(object):
    def __init__(self,name):
        self.name=name
        self.state="RELEASED"
        self.resource_time=0
        self.timestamp=0
        self.my_request_timestamp = 0
        self.request_queue = []
        self.lock = threading.Lock()

    """def get_fortune(self, name):
        return "Hello, {0}. Here is your fortune message:\n" \
               "Tomorrow's lucky number is 12345678.".format(name)"""
    
    def solicitar_recurso(self):
        with self.lock:
            self.state="WANTED"
        print(f"I want to enter the critical section and access resource")
        #Mandar msg pra cada peer, exceto pra ele próprio
        contador=0
        ns = Pyro5.api.locate_ns()  
        #verificar isso aqui!
        
        for peer_name in list(ns.list().keys())[1:]:         
            if peer_name==self.name:
                continue
            uri=ns.lookup(peer_name)
            peer=Pyro5.api.Proxy(uri)

            print(f"Solicitando recurso para {peer_name}")
            resposta=peer.receber_pedido(self.name)
            if resposta==True:
                contador+=1
            else:
               print(f"Você está na fila para acessar o recurso")  

        if contador == len(ns.list())-1:
            print(f"\nVocê pode acessar o recurso")
            self.state="HELD"            
            return True
        
    def receber_pedido(self, requester_name, request_timestamp):
        if (self.state=="WANTED" and self.my_request_timestamp < request_timestamp) or self.state=="HELD":
            self.request_queue.append((requester_name, request_timestamp))
            self.request_queue.sort(key=lambda x: (x[1], x[0]))
            return False
        else:
           return True
        
    def liberar_recurso(self):
        with self.lock:
            self.state="RELEASED"
            self.my_request_timestamp=0

        ns = Pyro5.api.locate_ns()  
        for requester_name in self.request_queue:
            uri = ns.lookup(requester_name)
            requester_proxy = Pyro5.api.Proxy(uri)
            print(f"Enviando permissão tardia para {requester_name}")
            requester_proxy.solicitar_recurso()             
        self.request_queue.clear()

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
            peer.solicitar_recurso()
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
    
