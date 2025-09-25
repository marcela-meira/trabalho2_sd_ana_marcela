import Pyro5.api

@Pyro5.api.expose
class Peer(object):
    def get_fortune(self, name):
        return "Hello, {0}. Here is your fortune message:\n" \
               "Tomorrow's lucky number is 12345678.".format(name)

name = input("What is your name? ").strip()

daemon = Pyro5.server.Daemon()         # make a Pyro daemon
ns = Pyro5.api.locate_ns()             # find the name server
uri = daemon.register(Peer)   # register the greeting maker as a Pyro object
ns.register(name, uri)   # register the object with a name in the name server

print("Ready.")
daemon.requestLoop()                   # start the event loop of the server to wait for calls



while True:
    opcao = input("Selecione a opcao desejada: \n 1. Solicitar recurso \n 2. Listar peers ativos \n 3. Liberar recurso \n 4. Sair \n")
    if(opcao=="1"):
        print("Solicitar recurso")
    elif(opcao=="2"):
        print("Liberar recurso")
    elif(opcao=="3"):
        print("Listar peers ativos")
    elif(opcao=="4"):
        exit()
    else:
        print("opcao invalida")
    
