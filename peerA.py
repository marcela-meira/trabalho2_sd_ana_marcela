import Pyro5.api

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
    