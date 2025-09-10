# -*- coding: utf-8 -*-

import zipfile
import time
import itertools
import string
import argparse
from tqdm import tqdm
import os
import multiprocessing
from typing import List, Tuple
import math

# -----------------------------------------------------------------------------
# FUNÇÃO WORKER (EXECUTADA POR CADA PROCESSO)
# -----------------------------------------------------------------------------
def worker(arquivo_zip: str, senhas: List[str], found_flag: multiprocessing.Event, progress_counter: multiprocessing.Value, lock: multiprocessing.Lock) -> None:
    """
    Função "trabalhadora" que testa um bloco de senhas.
    Executada por cada processo no modo paralelo.

    Args:
        arquivo_zip (str): Caminho para o ficheiro zip.
        senhas (List[str]): Uma lista (bloco) de senhas para testar.
        found_flag (multiprocessing.Event): Evento partilhado para sinalizar que a senha foi encontrada.
        progress_counter (multiprocessing.Value): Contador partilhado para a barra de progresso.
        lock (multiprocessing.Lock): Lock para garantir acesso seguro ao contador.
    """
    try:
        with zipfile.ZipFile(arquivo_zip, 'r') as zf:
            for senha in senhas:
                # Se outro processo já encontrou a senha, para de trabalhar
                if found_flag.is_set():
                    return

                try:
                    # Tenta extrair com a senha
                    zf.extractall(pwd=senha.encode('utf-8'))

                    # Se chegou aqui, a senha está correta!
                    with lock:
                        # Imprime o sucesso e define a flag para parar os outros workers
                        if not found_flag.is_set(): # Dupla verificação para evitar múltiplas mensagens
                            print("\n" + "-" * 50)
                            print(f"[SUCESSO] Senha encontrada: {senha}")
                            print("-" * 50)
                            found_flag.set()
                    return # Termina este worker

                except (RuntimeError, zipfile.BadZipFile):
                    # Senha incorreta, continua para a próxima
                    with lock:
                        progress_counter.value += 1
                    continue
    except Exception:
        # Lida com erros que podem ocorrer ao abrir o zip em um processo
        return

# -----------------------------------------------------------------------------
# LÓGICA DE TESTE (SEQUENCIAL E PARALELO)
# -----------------------------------------------------------------------------
def testar_senha_sequencial(arquivo_zip: str, min_len: int, max_len: int, charset: str) -> None:
    """Modo de força bruta tradicional, em uma única thread."""
    print("Modo de execução: Sequencial (single-thread)")
    inicio = time.time()
    tentativas_totais = 0

    for comprimento in range(min_len, max_len + 1):
        total_combinacoes = len(charset) ** comprimento
        combinacoes = itertools.product(charset, repeat=comprimento)

        for combinacao in tqdm(combinacoes, total=total_combinacoes, desc=f"Testando {comprimento} chars", unit="pwd"):
            senha = "".join(combinacao)
            tentativas_totais += 1
            try:
                with zipfile.ZipFile(arquivo_zip, 'r') as zf:
                    zf.extractall(pwd=senha.encode('utf-8'))

                fim = time.time()
                print("\n" + "-" * 50)
                print(f"[SUCESSO] Senha encontrada: {senha}")
                print(f"Total de tentativas: {tentativas_totais}")
                print(f"Tempo total: {fim - inicio:.2f} segundos")
                print("-" * 50)
                return
            except (RuntimeError, zipfile.BadZipFile):
                continue

    print(f"\n[FALHA] Senha não encontrada após {tentativas_totais} tentativas.")

def testar_senha_paralelo(arquivo_zip: str, min_len: int, max_len: int, charset: str, num_workers: int) -> None:
    """Modo de força bruta paralelo, usando múltiplos processos."""
    print(f"Modo de execução: Paralelo (usando {num_workers} processos)")
    inicio = time.time()

    manager = multiprocessing.Manager()
    found_flag = manager.Event()
    progress_counter = manager.Value('i', 0)
    lock = manager.Lock()

    with multiprocessing.Pool(processes=num_workers) as pool:
        for comprimento in range(min_len, max_len + 1):
            if found_flag.is_set():
                break

            print(f"\nGerando e distribuindo senhas de {comprimento} caracteres...")

            # Gera TODAS as senhas para o comprimento atual
            senhas = ["".join(p) for p in itertools.product(charset, repeat=comprimento)]
            total_combinacoes = len(senhas)

            # Divide a lista de senhas em blocos para cada worker
            tamanho_bloco = math.ceil(total_combinacoes / num_workers)
            blocos = [senhas[i:i + tamanho_bloco] for i in range(0, total_combinacoes, tamanho_bloco)]

            # Prepara os argumentos para cada worker
            tasks = [(arquivo_zip, bloco, found_flag, progress_counter, lock) for bloco in blocos]

            # Inicia os workers de forma assíncrona
            pool.starmap_async(worker, tasks)

            # Barra de progresso no processo principal
            with tqdm(total=total_combinacoes, desc=f"Testando {comprimento} chars", unit="pwd") as pbar:
                n = 0
                while n < total_combinacoes and not found_flag.is_set():
                    time.sleep(0.1) # Pequena pausa para não sobrecarregar a CPU
                    atual = progress_counter.value
                    pbar.update(atual - n)
                    n = atual

                # Se a senha foi encontrada, preenche a barra de progresso
                if found_flag.is_set():
                    pbar.update(total_combinacoes - n)

            # Reseta o contador de progresso para o próximo comprimento
            progress_counter.value = 0

    fim = time.time()
    if not found_flag.is_set():
        print("\n[FALHA] Senha não encontrada.")

    print(f"Tempo total: {fim - inicio:.2f} segundos")


# -----------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL E ANÁLISE DE ARGUMENTOS
# -----------------------------------------------------------------------------
def main() -> None:
    """Função principal que configura e executa o script."""
    parser = argparse.ArgumentParser(
        description="Simulador de teste de força de senha para ficheiros .zip.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Argumentos existentes
    parser.add_argument("arquivo_zip", help="O caminho para o ficheiro .zip.")
    parser.add_argument("-min", "--min_len", type=int, default=1, help="Comprimento mínimo da senha.")
    parser.add_argument("-max", "--max_len", type=int, default=8, help="Comprimento máximo da senha.")
    parser.add_argument("-d", "--digitos", action="store_true", help="Incluir dígitos (0-9).")
    parser.add_argument("-l", "--letras", action="store_true", help="Incluir letras minúsculas (a-z).")
    parser.add_argument("-u", "--maiusculas", action="store_true", help="Incluir letras maiúsculas (A-Z).")
    parser.add_argument("-s", "--simbolos", action="store_true", help="Incluir símbolos.")
    parser.add_argument("-a", "--alphanum", action="store_true", help="Atalho para letras e dígitos.")

    # NOVOS ARGUMENTOS para paralelismo
    parser.add_argument("-m", "--multithread", action="store_true", help="Ativar modo paralelo com múltiplos processos.")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help=f"Número de processos a serem utilizados (padrão: {os.cpu_count()}).")

    args = parser.parse_args()

    # Lógica de construção do charset (sem alterações)
    char_set = set()
    if args.alphanum: char_set.update(list(string.ascii_letters + string.digits))
    if args.digitos: char_set.update(list(string.digits))
    if args.letras: char_set.update(list(string.ascii_lowercase))
    if args.maiusculas: char_set.update(list(string.ascii_uppercase))
    if args.simbolos: char_set.update(list(string.punctuation))
    if not char_set: char_set.update(list(string.ascii_letters + string.digits))
    charset = "".join(sorted(list(char_set)))

    # Validação do ficheiro
    if not os.path.exists(args.arquivo_zip):
        print(f"[ERRO] O ficheiro '{args.arquivo_zip}' não foi encontrado.")
        return

    print("-" * 50)
    print(f"Alvo: {args.arquivo_zip}")
    print(f"Charset: '{charset[:40]}...' ({len(charset)} caracteres)")
    print(f"Comprimento: de {args.min_len} a {args.max_len}")
    print("-" * 50)

    # Decide qual função executar com base no argumento --multithread
    if args.multithread:
        testar_senha_paralelo(args.arquivo_zip, args.min_len, args.max_len, charset, args.workers)
    else:
        testar_senha_sequencial(args.arquivo_zip, args.min_len, args.max_len, charset)

if __name__ == "__main__":
    multiprocessing.freeze_support() # Suporte para Windows
    main()