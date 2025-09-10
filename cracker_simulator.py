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
import subprocess

try:
    import rarfile
    from rarfile import PasswordRequired
except ImportError:
    print("[AVISO] Biblioteca 'rarfile' não encontrada. O script não poderá processar ficheiros .rar.")
    print("Para instalar, execute: pip install rarfile")
    rarfile = None
    PasswordRequired = None


def testar_senha_rar_subprocess(file_path: str, senha: str) -> bool:
    """
    Testa uma senha em um arquivo RAR chamando o executável 'unrar' diretamente.
    """
    command = ['unrar', 't', f'-p{senha}', '-y', file_path]
    try:
        resultado = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
        return resultado.returncode == 0
    except FileNotFoundError:
        if not getattr(testar_senha_rar_subprocess, 'has_printed_error', False):
            print("\n[ERRO FATAL] O comando 'unrar' não foi encontrado no seu sistema.")
            print("Por favor, instale o 'unrar' e garanta que ele esteja no PATH do sistema.")
            testar_senha_rar_subprocess.has_printed_error = True
        return False
    except Exception:
        return False


def worker(extractor_details: tuple, senhas: list[str], found_flag: multiprocessing.Event, progress_counter: multiprocessing.Value, lock: multiprocessing.Lock) -> None:
    file_path, file_type = extractor_details
    archive_zip = None

    try:
        if file_type == 'zip':
            archive_zip = zipfile.ZipFile(file_path, 'r')
            first_file_zip = archive_zip.infolist()[0]

        for senha in senhas:
            if found_flag.is_set(): return

            senha_correta = False
            if file_type == 'zip':
                try:
                    archive_zip.read(first_file_zip.filename, pwd=senha.encode('utf-8'))
                    senha_correta = True
                except Exception:
                    senha_correta = False
            elif file_type == 'rar':
                senha_correta = testar_senha_rar_subprocess(file_path, senha)

            if senha_correta:
                with lock:
                    if not found_flag.is_set():
                        print(f"\n[SUCESSO] Senha encontrada: {senha}")
                        found_flag.set()
                return
            else:
                with lock:
                    progress_counter.value += 1
    finally:
        if archive_zip:
            archive_zip.close()

def testar_senha_sequencial(file_path: str, file_type: str, min_len: int, max_len: int, charset: str) -> None:
    print("Modo de execução: Sequencial (single-thread)")
    inicio = time.time()
    tentativas_totais = 0

    try:
        archive_zip = None
        first_file_zip = None
        if file_type == 'zip':
            archive_zip = zipfile.ZipFile(file_path, 'r')
            if not archive_zip.infolist():
                 print("\n[ERRO] O arquivo ZIP está vazio.")
                 return
            first_file_zip = archive_zip.infolist()[0]

        with archive_zip if archive_zip else open(os.devnull, 'w') as archive:
            for comprimento in range(min_len, max_len + 1):
                combinacoes = itertools.product(charset, repeat=comprimento)
                total_combinacoes = len(charset) ** comprimento

                for combinacao in tqdm(combinacoes, total=total_combinacoes, desc=f"Testando {comprimento} chars", unit="pwd"):
                    senha = "".join(combinacao)
                    tentativas_totais += 1
                    senha_correta = False

                    if file_type == 'zip':
                        try:
                            archive_zip.read(first_file_zip.filename, pwd=senha.encode('utf-8'))
                            senha_correta = True
                        except Exception:
                            senha_correta = False
                    elif file_type == 'rar':
                        senha_correta = testar_senha_rar_subprocess(file_path, senha)

                    if senha_correta:
                        fim = time.time()
                        print(f"\n[SUCESSO] Senha encontrada: {senha}")
                        print(f"Total de tentativas: {tentativas_totais}")
                        print(f"Tempo total: {fim - inicio:.2f} segundos")
                        return

        print(f"\n[FALHA] Senha não encontrada após {tentativas_totais} tentativas.")
    except Exception as e:
        print(f"\n[ERRO] Ocorreu um erro inesperado: {e}")

def testar_senha_paralelo(file_path: str, file_type: str, min_len: int, max_len: int, charset: str, num_workers: int) -> None:
    print(f"Modo de execução: Paralelo (usando {num_workers} processos)")
    inicio = time.time()
    manager = multiprocessing.Manager()
    found_flag = manager.Event()
    progress_counter = manager.Value('i', 0)
    lock = manager.Lock()
    extractor_details = (file_path, file_type)

    with multiprocessing.Pool(processes=num_workers) as pool:
        for comprimento in range(min_len, max_len + 1):
            if found_flag.is_set(): break
            print(f"\nGerando e distribuindo senhas de {comprimento} caracteres...")
            senhas = ["".join(p) for p in itertools.product(charset, repeat=comprimento)]
            total_combinacoes = len(senhas)
            tamanho_bloco = math.ceil(total_combinacoes / num_workers)
            blocos = [senhas[i:i + tamanho_bloco] for i in range(0, total_combinacoes, tamanho_bloco)]
            tasks = [(extractor_details, bloco, found_flag, progress_counter, lock) for bloco in blocos]
            async_result = pool.starmap_async(worker, tasks)
            with tqdm(total=total_combinacoes, desc=f"Testando {comprimento} chars", unit="pwd") as pbar:
                while not async_result.ready():
                    if found_flag.is_set(): break
                    pbar.n = progress_counter.value
                    pbar.refresh()
                    async_result.wait(timeout=0.05)
                pbar.n = progress_counter.value
                pbar.refresh()

    fim = time.time()
    if not found_flag.is_set():
        print("\n[FALHA] Senha não encontrada.")
    print(f"Tempo total: {fim - inicio:.2f} segundos")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador de teste de força de senha para ficheiros .zip e .rar.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("arquivo", help="O caminho para o ficheiro .zip ou .rar.")
    parser.add_argument("-min", "--min_len", type=int, default=1, help="Comprimento mínimo da senha.")
    parser.add_argument("-max", "--max_len", type=int, default=8, help="Comprimento máximo da senha.")
    parser.add_argument("-d", "--digitos", action="store_true", help="Incluir dígitos (0-9).")
    parser.add_argument("-l", "--letras", action="store_true", help="Incluir letras minúsculas (a-z).")
    parser.add_argument("-u", "--maiusculas", action="store_true", help="Incluir letras maiúsculas (A-Z).")
    parser.add_argument("-s", "--simbolos", action="store_true", help="Incluir símbolos.")
    ## CORREÇÃO: O valor de 'action' foi corrigido de True para "store_true".
    parser.add_argument("-a", "--alphanum", action="store_true", help="Atalho para letras e dígitos.")
    parser.add_argument("-m", "--multithread", action="store_true", help="Ativar modo paralelo com múltiplos processos.")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help=f"Número de processos a serem utilizados (padrão: {os.cpu_count()}).")
    args = parser.parse_args()

    file_path = args.arquivo
    file_type = None
    if file_path.lower().endswith('.zip'):
        file_type = 'zip'
    elif file_path.lower().endswith('.rar'):
        file_type = 'rar'
    else:
        print(f"[ERRO] Formato de ficheiro não suportado: '{file_path}'. Use .zip ou .rar.")
        return

    char_set = set()
    if args.alphanum: char_set.update(list(string.ascii_letters + string.digits))
    if args.digitos: char_set.update(list(string.digits))
    if args.letras: char_set.update(list(string.ascii_lowercase))
    if args.maiusculas: char_set.update(list(string.ascii_uppercase))
    if args.simbolos: char_set.update(list(string.punctuation))
    if not char_set: char_set.update(list(string.ascii_letters + string.digits))
    charset = "".join(sorted(list(char_set)))
    if not os.path.exists(file_path):
        print(f"[ERRO] O ficheiro '{file_path}' não foi encontrado.")
        return

    print("-" * 50)
    print(f"Alvo: {file_path} (Tipo: {file_type})")
    print(f"Charset: '{charset[:40]}...' ({len(charset)} caracteres)")
    print(f"Comprimento: de {args.min_len} a {args.max_len}")
    print("-" * 50)

    if args.multithread:
        testar_senha_paralelo(file_path, file_type, args.min_len, args.max_len, charset, args.workers)
    else:
        testar_senha_sequencial(file_path, file_type, args.min_len, args.max_len, charset)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()