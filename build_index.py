# build_index.py
import sys
import logging
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.core.settings import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

# Configura o logging para vermos o que está acontecendo
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

def main():
    try:
        print("--- Iniciando build_index.py ---")
        
        print("1. Configurando os modelos (Ollama)...")
        # ATENÇÃO: Confirme que os nomes dos modelos estão corretos
        Settings.llm = Ollama(model="llama3:8b")
        Settings.embed_model = OllamaEmbedding(model_name="mxbai-embed-large") # Você mencionou este modelo, confirme

        print("2. Carregando documentos da pasta 'docs/'...")
        # Garanta que a pasta 'docs' existe e tem arquivos dentro
        documents = SimpleDirectoryReader("docs").load_data()
        
        if not documents:
            print("\n!!! ERRO: Nenhum documento encontrado na pasta 'docs/'. !!!")
            print("Por favor, adicione arquivos (.pdf, .txt, .md) na pasta 'docs' e tente novamente.")
            return

        print(f"-> {len(documents)} documento(s) carregado(s).")

        print("3. Criando o índice vetorial (isso pode demorar)...")
        # Esta é a linha que cria o índice em memória
        index = VectorStoreIndex.from_documents(documents)

        print("4. Salvando o índice em disco na pasta './storage'...")
        # Esta é a linha que CRIA a pasta e os arquivos (como docstore.json)
        index.storage_context.persist(persist_dir="./storage")

        print("\n--- Processo Concluído! ---")
        print("A pasta 'storage/' foi criada com sucesso.")
        print("Agora você pode rodar 'python app.py'")

    except Exception as e:
        print(f"\n!!! Ocorreu um erro DURANTE A CONSTRUÇÃO do índice: {e} !!!")
        print("\nPor favor, verifique:")
        print("1. O Ollama está rodando? (Rode 'ollama list' em outro terminal)")
        print("2. Os modelos 'llama3:8b' e 'mxbai-embed-large' estão baixados? (Rode 'ollama pull mxbai-embed-large')")
        print("3. A pasta 'docs/' existe e contém arquivos?")
        
        # Imprime o traceback completo para debug
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
