import os
import shutil

class TabelaHash:
    def __init__(self, tamanho=100):
        self.tamanho = tamanho
        self.vetor = [[] for _ in range(tamanho)]
    
    def funcao_hash(self, tamanho):
        return tamanho % self.tamanho
    
    def inserir(self, tamanho, caminho):
        indice = self.funcao_hash(tamanho)
        self.vetor[indice].append((tamanho, caminho))
    
    def buscar_por_tamanho(self, tamanho):
        indice = self.funcao_hash(tamanho)
        return [caminho for tam, caminho in self.vetor[indice] if tam == tamanho]

def comparar_arquivos(arquivo1, arquivo2):
    """Compara dois arquivos byte a byte"""
    try:
        if os.path.getsize(arquivo1) != os.path.getsize(arquivo2):
            return False
            
        with open(arquivo1, 'rb') as f1, open(arquivo2, 'rb') as f2:
            while True:
                conteudo1 = f1.read(4096)
                conteudo2 = f2.read(4096)
                if conteudo1 != conteudo2:
                    return False
                if not conteudo1:
                    return True
    except:
        return False

def main():
    tabela = TabelaHash()
    
    dir_origem = input("Digite a pasta de origem: ").strip()
    dir_destino = input("Digite a pasta de destino: ").strip()
    
    if not os.path.exists(dir_origem):
        print(f" ERRO: A pasta '{dir_origem}' não existe!")
        return
    
    os.makedirs(dir_destino, exist_ok=True)
    
    print(f"\n Procurando arquivos em: {dir_origem}")
    print("=" * 60)
    

    total_arquivos = 0
    arquivos_copiados = 0
    duplicatas = 0
    

    for pasta_atual, _, arquivos in os.walk(dir_origem):
        for nome_arquivo in arquivos:
            total_arquivos += 1
            caminho_completo = os.path.join(pasta_atual, nome_arquivo)
            
            try:
                tamanho = os.path.getsize(caminho_completo)
                
                existentes = tabela.buscar_por_tamanho(tamanho)
                duplicado = False
                
                if existentes:
                    for arquivo_existente in existentes:
                        if comparar_arquivos(caminho_completo, arquivo_existente):
                            print(f" ARQUIVO DUPLICADO: {nome_arquivo} (igual a {os.path.basename(arquivo_existente)})")
                            duplicatas += 1
                            duplicado = True
                            break
                
                if not duplicado:
                    destino_final = os.path.join(dir_destino, nome_arquivo)
                    

                    contador = 1
                    while os.path.exists(destino_final):
                        nome, ext = os.path.splitext(nome_arquivo)
                        destino_final = os.path.join(dir_destino, f"{nome}_{contador}{ext}")
                        contador += 1
                    
                    shutil.copy2(caminho_completo, destino_final)
                    tabela.inserir(tamanho, destino_final)
                    arquivos_copiados += 1
                    print(f" COPIADO: {nome_arquivo} ({tamanho} bytes)")
                        
            except Exception as e:
                print(f" ERRO processando {nome_arquivo}: {e}")
    
    # Resultado final
    print("=" * 60)
    print("RESULTADO:")
    print(f"Total de arquivos encontrados: {total_arquivos}")
    print(f"Arquivos únicos copiados: {arquivos_copiados}")
    print(f"Arquivos duplicados: {duplicatas}")
    print(f"Pasta destino: {dir_destino}")
    
    # Mostra estatísticas da tabela hash
    print(f"\nEstatísticas da Tabela Hash:")
    print(f"Tamanho do vetor: {tabela.tamanho}")
    indices_ocupados = sum(1 for lista in tabela.vetor if lista)
    print(f"Índices ocupados: {indices_ocupados}/{tabela.tamanho}")

if __name__ == "__main__":
    main()