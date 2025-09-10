# -*- coding: utf-8 -*-

import zipfile
import time
import itertools
import string
import argparse
from tqdm import tqdm
import os
import multiprocessing
import math

# A função worker permanece a mesma, já estava correta.
def worker(arquivo_zip: str, senhas: list[str], found_flag: multiprocessing.Event, progress_counter: multiprocessing.Value, lock: multiprocessing.Lock) -> None:
    try:
        with zipfile.ZipFile(arquivo_zip, 'r') as zf:
            for senha in senhas:
                if found_flag.is_set():
                    return
                try:
                    zf.extractall(pwd=senha.encode('utf-8'))
                    with lock:
                        if not found_flag.is_set():
                            print("\n" + "-" * 50)
                            print(f"[SUCESSO] Senha encontrada: {senha}")
                            print("-" * 50)
                            found_flag.set()
                    return
                except (RuntimeError, zipfile.BadZipFile):
                    with lock:
                        progress_counter.value += 1
                    continue
    except Exception:
        return

# -----------------------------------------------------------------------------
# LÓGICA DE TESTE (SEQUENCIAL E PARALELO) - AGORA CORRIGIDAS
# -----------------------------------------------------------------------------
def testar_senha_sequencial(arquivo_zip: str, min_len: int, max_len: int, charset: str) -> None:
    """Modo de força bruta tradicional, em uma única thread (AGORA OTIMIZADO)."""
    print("Modo de execução: Sequencial (single-thread)")
    inicio = time.time()
    tentativas_totais = 0

    try:
        ## CORREÇÃO: O 'with' foi movido para fora do loop, abrindo o ficheiro apenas UMA VEZ.
        with zipfile.ZipFile(arquivo_zip, 'r') as zf:
            for comprimento in range(min_len, max_len + 1):
                total_combinacoes = len(charset) ** comprimento
                combinacoes = itertools.product(charset, repeat=comprimento)

                for combinacao in tqdm(combinacoes, total=total_combinacoes, desc=f"Testando {comprimento} chars", unit="pwd"):
                    senha = "".join(combinacao)
                    tentativas_totais += 1
                    try:
                        # O ficheiro já está aberto, a verificação é muito mais rápida.
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

    except FileNotFoundError:
        print(f"\n[ERRO] O ficheiro .zip '{arquivo_zip}' não foi encontrado.")
    except Exception as e:
        print(f"\n[ERRO] Ocorreu um erro inesperado: {e}")

def testar_senha_paralelo(arquivo_zip: str, min_len: int, max_len: int, charset: str, num_workers: int) -> None:
    """Modo de força bruta paralelo, usando múltiplos processos (AGORA OTIMIZADO)."""
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
            senhas = ["".join(p) for p in itertools.product(charset, repeat=comprimento)]
            total_combinacoes = len(senhas)
            tamanho_bloco = math.ceil(total_combinacoes / num_workers)
            blocos = [senhas[i:i + tamanho_bloco] for i in range(0, total_combinacoes, tamanho_bloco)]
            tasks = [(arquivo_zip, bloco, found_flag, progress_counter, lock) for bloco in blocos]

            # Inicia os workers de forma assíncrona
            async_result = pool.starmap_async(worker, tasks)

            # ## CORREÇÃO: Loop de monitorização da barra de progresso otimizado.
            # Em vez de um 'sleep' longo, usamos 'wait' com um timeout curto,
            # tornando a atualização muito mais responsiva e rápida.
            with tqdm(total=total_combinacoes, desc=f"Testando {comprimento} chars", unit="pwd") as pbar:
                while not async_result.ready():
                    if found_flag.is_set():
                        break
                    pbar.n = progress_counter.value
                    pbar.refresh()
                    async_result.wait(timeout=0.05) # Espera no máximo 0.05s

                # Atualização final para garantir que a barra chegue a 100%
                pbar.n = progress_counter.value
                pbar.refresh()

    fim = time.time()
    if not found_flag.is_set():
        print("\n[FALHA] Senha não encontrada.")

    print(f"Tempo total: {fim - inicio:.2f} segundos")

# A função main permanece a mesma.
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador de teste de força de senha para ficheiros .zip.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("arquivo_zip", help="O caminho para o ficheiro .zip.")
    parser.add_argument("-min", "--min_len", type=int, default=1, help="Comprimento mínimo da senha.")
    parser.add_argument("-max", "--max_len", type=int, default=8, help="Comprimento máximo da senha.")
    parser.add_argument("-d", "--digitos", action="store_true", help="Incluir dígitos (0-9).")
    parser.add_argument("-l", "--letras", action="store_true", help="Incluir letras minúsculas (a-z).")
    parser.add_argument("-u", "--maiusculas", action="store_true", help="Incluir letras maiúsculas (A-Z).")
    parser.add_argument("-s", "--simbolos", action="store_true", help="Incluir símbolos.")
    parser.add_argument("-a", "--alphanum", action="store_true", help="Atalho para letras e dígitos.")
    parser.add_argument("-m", "--multithread", action="store_true", help="Ativar modo paralelo com múltiplos processos.")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help=f"Número de processos a serem utilizados (padrão: {os.cpu_count()}).")
    args = parser.parse_args()

    char_set = set()
    if args.alphanum: char_set.update(list(string.ascii_letters + string.digits))
    if args.digitos: char_set.update(list(string.digits))
    if args.letras: char_set.update(list(string.ascii_lowercase))
    if args.maiusculas: char_set.update(list(string.ascii_uppercase))
    if args.simbolos: char_set.update(list(string.punctuation))
    if not char_set: char_set.update(list(string.ascii_letters + string.digits))
    charset = "".join(sorted(list(char_set)))

    if not os.path.exists(args.arquivo_zip):
        print(f"[ERRO] O ficheiro '{args.arquivo_zip}' não foi encontrado.")
        return

    print("-" * 50)
    print(f"Alvo: {args.arquivo_zip}")
    print(f"Charset: '{charset[:40]}...' ({len(charset)} caracteres)")
    print(f"Comprimento: de {args.min_len} a {args.max_len}")
    print("-" * 50)

    if args.multithread:
        testar_senha_paralelo(args.arquivo_zip, args.min_len, args.max_len, charset, args.workers)
    else:
        testar_senha_sequencial(args.arquivo_zip, args.min_len, args.max_len, charset)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()