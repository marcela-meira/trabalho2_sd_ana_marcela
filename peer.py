''' Para iniciar o servidor no terminal usar:
    python -m Pyro5.nameserver
'''

import Pyro5.api
from Pyro5.server import Daemon
import threading

@Pyro5.api.expose
class Peer(object):
    def get_fortune(self, name):
        return "Hello, {0}. Here is your fortune message:\n" \
               "Tomorrow's lucky number is 12345678.".format(name)

name = input("What is your name? ").strip()

daemon = Pyro5.server.Daemon()         # make a Pyro daemon
ns = Pyro5.api.locate_ns()             # find the name server
if name not in ns.list().keys():
    uri = daemon.register(Peer)   # register the greeting maker as a Pyro object
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
        print("Solicitar recurso")
    elif opcao == "2":
        print("Listar peers ativos")
        print(ns.list())  # exemplo: mostra peers registrados
    elif opcao == "3":
        print("Liberar recurso")
    elif opcao == "4":
        print("Encerrando...")
        ns.remove(name)   # remove peer do NameServer
        break
    else:
        print("Opção inválida")
    
