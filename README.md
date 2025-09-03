## Alunos  
| Matrícula | Nome |  
|-----------------------|---------------------|  
| 20/0025058 | Mayara Alves de Oliveira |  
| 20/2016720 | Luana Ribeiro Soares     |  

## Descrição do projeto
O algoritmo analisa o tamanho de um arquivo e utiliza esse valor como chave para armazenamento em uma estrutura hash. Antes de adicionar o arquivo ao diretório de destino, o sistema verifica se já existe algum arquivo com o mesmo tamanho registrado. Caso exista, é iniciado um processo de comparação de conteúdo entre os arquivos para confirmar se são idênticos. Se forem iguais, o arquivo é descartado e o usuário é informado sobre a duplicata. Se forem diferentes, o endereço do arquivo é adicionado à tabela hash utilizando uma lista encadeada para tratar os conflitos, e o arquivo é copiado para o diretório de destino. Essa abordagem garante que apenas arquivos únicos sejam armazenados, enquanto duplicates são identificados e rejeitados.

## Guia de instalação

### Dependências do projeto

### Como executar o projeto

## Capturas de tela

## Conclusões

## Referências

