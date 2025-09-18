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
import json
from datetime import datetime
import copy
import operator
import rarfile

# -----------------------------------------------------------------------------
# CLASSE DEDICADA PARA GERIR SESSÕES
# -----------------------------------------------------------------------------
class SessionManager:
    """
    Gere o ficheiro de sessão para salvar e retomar o progresso.
    """
    def __init__(self, filepath='cracker_sessions.json'):
        self.filepath = filepath
        self.sessions = self._load()

    def _load(self) -> dict:
        """Carrega as sessões do ficheiro JSON. Retorna um dict vazio se não existir."""
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self) -> None:
        """Salva o dicionário de sessões no ficheiro JSON de forma atómica."""
        temp_filepath = self.filepath + '.tmp'
        with open(temp_filepath, 'w') as f:
            json.dump(self.sessions, f, indent=4)
        os.replace(temp_filepath, self.filepath) # Operação atómica

    def get_session(self, target_path: str) -> dict | None:
        """Obtém os dados de uma sessão para um arquivo alvo específico."""
        abs_path = os.path.abspath(target_path)
        return self.sessions.get(abs_path)

    def update_session(self, target_path: str, session_data: dict) -> None:
        """Cria ou atualiza os dados de uma sessão e salva no ficheiro."""
        abs_path = os.path.abspath(target_path)
        # Garante que os dados mais recentes estão no objeto antes de salvar
        self.sessions[abs_path] = session_data
        self._save()

    def remove_session(self, target_path: str) -> None:
        """Remove uma sessão específica do ficheiro."""
        abs_path = os.path.abspath(target_path)
        if abs_path in self.sessions:
            del self.sessions[abs_path]
            self._save()

    def delete_file(self) -> None:
        """Apaga o ficheiro de sessões."""
        try:
            os.remove(self.filepath)
            self.sessions = {}
        except FileNotFoundError:
            pass

# RAR_METHOD_TEST pode ser 'rarfile' ou 'subprocess'
# 'subprocess' é mais robusto, mas depende do comando 'unrar' estar instalado
# 'rarfile' é mais direto, mas pode ter problemas de concorrência em alguns sistemas
RAR_METHOD_TEST = 'rarfile'

# ZIP_METHOD_TEST pode ser 'zipfile' ou 'subprocess'
# 'zipfile' é a biblioteca padrão do Python, mas pode ter problemas com alguns arquivos
# 'subprocess' usa o comando 'unzip' do sistema, que pode ser mais robusto
ZIP_METHOD_TEST = 'zipfile'

class PasswordNotNeeded(Exception):
    """Exceção personalizada para indicar que o arquivo não precisa de senha."""
    pass

# Função para criar um arquivo de teste ZIP/RAR com senha
def criar_arquivo_teste(file_path, senha, type='zip'):
    """Cria um arquivo rar de teste com senha."""
    if os.path.exists(file_path):
        return

    print(f"Criando arquivo de teste '{file_path}' com senha {senha}...")

    text_file = 'documento.txt'

    with open(text_file, "w") as f:
        f.write("Este é um teste de conteúdo para o benchmark.")

    try:
        # Usa processo para criar o arquivo com senha
        if type == 'zip':
            command = ['zip', '-P', senha, '-j', file_path, text_file]
        else:
            command = ['rar', 'a', f'-hp{senha}', '-y', file_path, text_file]

        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print("Arquivo de teste criado.\n")
    except Exception as e:
        print(f"Erro ao criar arquivo de teste: {e}")
    finally:
        if os.path.exists(text_file):
            os.remove(text_file)

# Testar senha RAR usando subprocess para evitar problemas de concorrência
def testar_senha_rar_subprocess(file_path: str, senha: str) -> bool:
    """Usa o método 'subprocess' para testar arquivos RAR. Certifique-se de que o comando 'unrar' está instalado."""
    command = ['unrar', 't', f'-p{senha}', '-y', file_path]
    try:
        # Caso seja a primeira execução, verifica se o arquivo precisa de senha
        # Não funciona como esperado, cada nova chamada ao método o atribituo é resetado
        if (not getattr(testar_senha_rar_subprocess, 'first_run_done', False)):
            command =  ['unrar', 't', '-y', file_path]
            resultado = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if resultado.returncode == 0:
                raise PasswordNotNeeded
            testar_senha_rar_subprocess.first_run_done = True
        resultado = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return resultado.returncode == 0
    except PasswordNotNeeded:
        raise PasswordNotNeeded(f'[INFO] O arquivo {file_path} não precisa de senha.')
    except Exception as e:
        if not getattr(testar_senha_rar_subprocess, 'has_printed_error', False):
            testar_senha_rar_subprocess.has_printed_error = True
            print(f"\n[ERRO] Ocorreu um erro ao testar o arquivo {file_path}! ({type(e).__name__}:  {str(e)}).")
            exit(1)
        return False

# Testar senha RAR usando a biblioteca rarfile
def testar_senha_rar_rarfile(file_path: str, senha: str) -> bool:
    try:
        # print(f"Testando senha RAR com rarfile: {senha}")
        with rarfile.RarFile(file_path, 'r') as rf:
            needs_password = rf.needs_password()
            if not needs_password:
                raise PasswordNotNeeded
            rf.setpassword(senha)
            rf.testrar()
        return True
    except rarfile.NoCrypto:
        return needs_password
    except rarfile.RarWrongPassword:
        # print(f"Senha incorreta: {senha}")
        return False
    except PasswordNotNeeded:
        raise PasswordNotNeeded(f'[INFO] O arquivo {file_path} não precisa de senha.')
    except Exception as e:
        # if not getattr(testar_senha_rar_rarfile, 'has_printed_error', False):
            # testar_senha_rar_rarfile.has_printed_error = True
        print(f"\n[ERRO] Ocorreu um erro ao testar o arquivo {file_path}! ({type(e).__name__}:  {str(e)}).")
        return False

# Função wrapper para escolher o método de teste RAR
def testar_senha_rar(file_path: str, senha: str) -> bool:
    if RAR_METHOD_TEST == 'subprocess':
        return testar_senha_rar_subprocess(file_path, senha)
    else:
        return testar_senha_rar_rarfile(file_path, senha)

# Testar senha ZIP usando subprocess para evitar problemas de concorrência
def testar_senha_zip_subprocess(file_path: str, senha: str) -> bool:
    command = ['unzip', '-t', '-P', senha, file_path]
    try:
        resultado = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return resultado.returncode == 0
    except Exception as e:
        if not getattr(testar_senha_zip_subprocess, 'has_printed_error', False):
            testar_senha_zip_subprocess.has_printed_error = True
            print(f"\n[ERRO] Ocorreu um erro ao testar o arquivo {file_path}! ({type(e).__name__}:  {str(e)}).")
            exit(1)
        return False

# Testar senha ZIP usando a biblioteca zipfile
def testar_senha_zip_zipfile(file_path: str, senha: str) -> bool:
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            zf.read(zf.infolist()[0].filename, pwd=senha.encode('utf-8'))
            return True
    except Exception:
        return False

# Função wrapper para escolher o método de teste ZIP
def testar_senha_zip(file_path: str, senha: str) -> bool:
    if ZIP_METHOD_TEST == 'subprocess':
        return testar_senha_zip_subprocess(file_path, senha)
    else:
        return testar_senha_zip_zipfile(file_path, senha)

# O worker agora é muito mais simples.
# Ele recebe UMA tarefa e retorna o resultado.
def worker(task_args) -> tuple[bool, str | None]:
    # time.sleep(0.01)
    """
    Worker que testa UMA senha e retorna se foi bem-sucedido.
    """
    file_path, file_type, senha = task_args
    senha_correta = False

    if file_type == 'zip':
        try:
            # Reabre o ficheiro aqui para segurança entre processos
            with zipfile.ZipFile(file_path, 'r') as zf:
                zf.read(zf.infolist()[0].filename, pwd=senha.encode('utf-8'))
                senha_correta = True
        except Exception:
            pass
    elif file_type == 'rar':
        senha_correta = testar_senha_rar(file_path, senha)

    return (True, senha) if senha_correta else (False, senha)

# Testa senhas de forma sequencial
# A função agora aceita 'session_manager' e 'session_data'
def testar_senha_sequencial(session_manager: SessionManager, session_data: dict, testing: bool = False) -> None:
    file_path = session_data['target_file']
    file_type = session_data['file_type']
    min_len = session_data['current_len']
    max_len = session_data['max_len']
    charset = session_data['charset']
    start_step = session_data['last_step']

    print("Modo de execução: Sequencial (single-thread)")
    inicio = time.perf_counter()
    tentativas_totais = 0
    senha_correta = False
    SAVE_INTERVAL = 1000 # Salva o progresso a cada 1000 tentativas no modo sequencial

    try:
        archive_zip = None
        first_file_zip = None
        if file_type == 'zip':
            archive_zip = zipfile.ZipFile(file_path, 'r')
            if not archive_zip.infolist():
                print("\n[ERRO] O arquivo ZIP está vazio.")
                return
            first_file_zip = archive_zip.infolist()[0]

        for comprimento in range(min_len, max_len + 1):
            if senha_correta: break

            session_data['current_len'] = comprimento
            total_combinacoes = len(charset) ** comprimento
            combinacoes = itertools.product(charset, repeat=comprimento)

            # Lógica para saltar para o 'step' inicial
            initial_step = 0
            if start_step > 0 and comprimento == min_len:
                print(f"Saltando para o laço inicial {start_step}...\n")
                combinacoes = itertools.islice(combinacoes, start_step, None)
                initial_step = start_step

            print(f"\nIniciando testes para senhas de {comprimento} caractere(s)...\n")

            # A barra de progresso agora usa o parâmetro 'initial'
            for combinacao in tqdm(combinacoes, total=total_combinacoes, desc=f"Testando {comprimento} caracteres(s)", unit="pwd", initial=initial_step, dynamic_ncols=True):
                senha = "".join(combinacao)
                tentativas_totais += 1
                senha_correta = False

                session_data['last_password'] = senha

                # Salvamento periódico
                if not testing and (tentativas_totais > 0 and tentativas_totais % SAVE_INTERVAL == 0):
                    session_data['last_step'] = tentativas_totais
                    session_data['last_update'] = datetime.now().isoformat()
                    session_manager.update_session(file_path, session_data)

                if file_type == 'zip':
                    try:
                        archive_zip.read(first_file_zip.filename, pwd=senha.encode('utf-8'))
                        senha_correta = True
                    except Exception:
                        pass
                elif file_type == 'rar':
                    senha_correta = testar_senha_rar(file_path, senha)

                if senha_correta:
                    break

            # Reseta o start_step para o próximo comprimento de senha
            start_step = 0

        fim = time.perf_counter()
        total_time = fim - inicio
        rate = tentativas_totais / total_time if total_time > 0 else 0

        # Atualiza o estado final da sessão
        session_data['last_step'] = tentativas_totais
        session_data['last_update'] = datetime.now().isoformat()

        print("\n" + "-" * 50)

        if senha_correta:
            session_data['status'] = 'found'
            session_data['found_password'] = senha

            print(f"\n[SUCESSO] Senha encontrada: {senha}")
            print(f"\nTotal de tentativas: {tentativas_totais}")
        else:
            session_data['status'] = 'failed'
            print(f"\n[FALHA] Senha não encontrada após {tentativas_totais} tentativas.")

        print(f"\nTempo total: {total_time:.4f} segundos\n")
        print("-" * 50)

        if not testing:
            session_manager.update_session(file_path, session_data)

        return {'modo': 'Sequencial', 'workers': 'N/A', 'chunksize': 'N/A', 'tempo': (total_time), 'rate': rate, 'founded': senha is not None}

    except PasswordNotNeeded as pn:
        print(f"\n{pn}")
        session_data['status'] = 'no_password_needed'
        if not testing:
            session_manager.update_session(file_path, session_data)
    except Exception as e:
        print(f"\n[ERRO] Ocorreu um erro inesperado: {e}")

# A função paralela agora usa 'imap_unordered' para latência mínima.
# A função agora aceita 'start_step'
def testar_senha_paralelo(session_manager: SessionManager, session_data: dict, num_workers: int, chunksize: int, testing: bool = False) -> None:
    # Extrai parâmetros da sessão
    file_path = session_data['target_file']
    file_type = session_data['file_type']
    # Começa sempre do comprimento guardado
    min_len = session_data['current_len']
    max_len = session_data['max_len']
    charset = session_data['charset']
    start_step = session_data['last_step']

    print(f"Modo de execução: Paralelo (usando {num_workers} processo(s))")
    inicio = time.perf_counter()
    senha_encontrada = None
    # Salva o progresso a cada 1000 tentativas
    SAVE_INTERVAL = 1000

    try:
        for comprimento in range(min_len, max_len + 1):
            if senha_encontrada: break

            session_data['current_len'] = comprimento
            total_combinacoes = len(charset) ** comprimento
            # Cria um gerador de senhas (eficiente em memória)
            senhas_generator = ("".join(p) for p in itertools.product(charset, repeat=comprimento))

            # Lógica para saltar para o 'step' inicial
            initial_step = 0
            if start_step > 0 and comprimento == min_len:
                print(f"Saltando para o laço inicial {start_step}...")
                senhas_generator = itertools.islice(senhas_generator, start_step, None)
                initial_step = start_step

            # Cria um gerador de tarefas para os workers
            tasks_generator = ((file_path, file_type, s) for s in senhas_generator)

            print(f"\nIniciando testes para senhas de {comprimento} caracteres(s)...\n")

            # A barra de progresso agora usa o parâmetro 'initial'
            with multiprocessing.Pool(processes=num_workers) as pool, \
            tqdm(total=total_combinacoes, desc=f"Testando {comprimento} caracteres(s)", unit="pwd", initial=initial_step, dynamic_ncols=True, mininterval=0.01) as pbar:
                # imap_unordered distribui as tarefas e retorna os resultados assim que ficam prontos
                for sucesso, senha in pool.imap_unordered(worker, tasks_generator, chunksize):
                    pbar.update(1)
                    session_data['last_password'] = senha

                    # Salvamento periódico
                    if not testing and (pbar.n > 0 and pbar.n % SAVE_INTERVAL == 0):
                        session_data['last_step'] = pbar.n
                        session_data['last_update'] = datetime.now().isoformat()
                        session_manager.update_session(file_path, session_data)

                    if sucesso:
                        senha_encontrada = senha
                        pool.terminate()
                        # pbar.update(total_combinacoes - pbar.n)
                        break

            # Reseta o start_step para o próximo comprimento de senha
            start_step = 0

        fim = time.perf_counter()
        total_time = fim - inicio

        # Captura a taxa de processamento manual
        tentativas_totais = sum(len(charset) ** i for i in range(min_len, (comprimento if comprimento > min_len else min_len))) + pbar.n
        rate = tentativas_totais / total_time if total_time > 0 else 0

        # print(f"\nTaxa de processamento (manual): {rate:.2f} senhas/segundo")
        # print(f"Total de combinações: {tentativas_totais}")
        # print(f"Tempo total: {total_time:.2f} segundos")

        # Atualiza o estado final da sessão
        session_data['last_step'] = pbar.n
        session_data['last_update'] = datetime.now().isoformat()

        print("\n" + "-" * 50)

        if senha_encontrada:
            # A mensagem de sucesso é movida para aqui para garantir que aparece depois da barra de progresso
            session_data['status'] = 'found'
            session_data['found_password'] = senha

            print(f"\n[SUCESSO] Senha encontrada: {senha_encontrada}")
            print(f"\nTotal de tentativas: {tentativas_totais}")
        else:
            session_data['status'] = 'failed'
            print(f"\n[FALHA] Senha não encontrada após {tentativas_totais} tentativas.")

        print(f"\nTempo total: {total_time:.4f} segundos\n")
        print("-" * 50)

        if not testing:
            session_manager.update_session(file_path, session_data)

        return {'modo': 'Paralelo', 'workers': num_workers, 'chunksize': chunksize, 'tempo': (total_time), 'rate': rate, 'founded': senha_encontrada is not None}

    except PasswordNotNeeded as pn:
        print(f"\n{pn}")
        session_data['status'] = 'no_password_needed'
        if not testing:
            session_manager.update_session(file_path, session_data)
    except Exception as e:
        print(f"\n[ERRO] Ocorreu um erro inesperado: {e}")

# Testes de desempenho com diferentes números de workers e chunksizes
def benchmark(args, file_path) -> None:

    file_path = file_path or ('benchmark.zip' if args.benchmark else 'benchmark.rar')

    criar_arquivo_teste(file_path, '890', 'rar' if file_path.lower().endswith('.rar') else 'zip')

    session_manager = SessionManager('test_sessions.json')

    # Adiciona um conjunto padrão de caracteres
    char_set = set()
    charset = char_set.update(list(string.digits))
    charset = "".join(sorted(list(char_set)))

    args.min_len = 1
    args.max_len = 3

    file_type = None
    if file_path.lower().endswith('.zip'):
        file_type = 'zip'
    elif file_path.lower().endswith('.rar'):
        file_type = 'rar'
    else:
        print(f"[ERRO] Formato de ficheiro não suportado: '{file_path}'. Use .zip ou .rar.")
        return

    if not os.path.exists(file_path):
        print(f"[ERRO] O ficheiro '{file_path}' não foi encontrado.")
        return

    # Cria a nova estrutura de dados da sessão
    session_data = {
        "target_file": os.path.abspath(file_path),
        "file_type": file_type,
        "charset_args": {
            "digits": args.digitos,
            "letters": args.letters,
            "lowercase": args.lowercase,
            "uppercase": args.uppercase,
            "symbols": args.simbolos,
            "alphanum": args.alphanum
        },
        "charset": charset,
        "min_len": args.min_len,
        "max_len": args.max_len,
        "current_len": args.min_len,
        "last_step": 0,
        "status": "running",
        "found_password": None,
        "last_password": None,
        "last_update": datetime.now().isoformat()
    }
    session_manager.update_session(file_path, copy.deepcopy(session_data))

    # Armazenamento dos resultados dos testes
    resultados_testes = []

    print("\n" + ("-" * 50))
    print("# Testes de desempenho\n" )

    print("-" * 50)
    print(f"CPU Count: {multiprocessing.cpu_count()}\n")
    print(f"Alvo: {file_path} (Tipo: {file_type})\n")
    print(f"Charset: '{charset[:40]}...' ({len(charset)} caracteres)\n")
    print(f"Comprimento: de {args.min_len} a {args.max_len}\n")
    print("-" * 50)

    print("\n" + ("-" * 50))
    print("#  Sequencial\n" )
    result = testar_senha_sequencial(session_manager, copy.deepcopy(session_data), True)
    session_manager.update_session(file_path, copy.deepcopy(session_data))
    resultados_testes.append(result)

    print("\n" + ("-" * 50))
    print("# Paralelos" )

    for workers in [4, 8, 16, 32, 64, 128]:
        args.workers = workers

        for chunksize in [1, 2, 5, 10, 20, 50]:
            print("\n" + ("-" * 50))
            print(f"Workers: {args.workers}, Chunksize: {chunksize}")
            print("-" * 50)
            result = testar_senha_paralelo(session_manager, copy.deepcopy(session_data), args.workers, chunksize, True)
            session_manager.update_session(file_path, copy.deepcopy(session_data))
            resultados_testes.append(result)

    session_manager.delete_file()

    # Ordena os resultados pelo tempo
    if (resultados_testes):
        resultados_testes.sort(key=operator.itemgetter('tempo'))
        print("\n--- Tabela de Desempenho ---")
        formatar_tabela(resultados_testes)
    else:
        print("Nenhum resultado de teste disponível.")

    # Limpa arquivo de teste
    if file_path in ['benchmark.zip', 'benchmark.rar'] and os.path.exists(file_path):
        os.remove(file_path)

# Função para formatar e exibir a tabela de resultados
def formatar_tabela(dados):
    """Formata e exibe os dados em uma tabela no terminal."""
    if not dados:
        print("Nenhum dado para exibir.")
        return

    # Encontra a largura máxima para cada coluna para alinhamento
    # Inclui os cabeçalhos na verificação para garantir que caibam
    largura_pos = len("Posição")
    largura_modo = len("Modo de Execução")
    largura_workers = len("Workers")
    largura_chunksize = len("Chunksize")
    largura_tempo = len("Tempo (s)")
    largura_taxa = len("Taxa (it/s)")

    for i, linha in enumerate(dados):
        if len(str(i + 1)) > largura_pos:
            largura_pos = len(str(i + 1))
        if len(linha['modo']) > largura_modo:
            largura_modo = len(linha['modo'])
        if len(str(linha['workers'])) > largura_workers:
            largura_workers = len(str(linha['workers']))
        if len(str(linha['chunksize'])) > largura_chunksize:
            largura_chunksize = len(str(linha['chunksize']))
        if len(f"{linha['tempo']:.4f}") > largura_tempo:
            largura_tempo = len(f"{linha['tempo']:.4f}")
        if len(f"{linha['rate']:.2f}") > largura_taxa:
            largura_taxa = len(f"{linha['rate']:.2f}")

    # Cria o formato da linha da tabela
    formato_linha = (
        f"| {{:<{largura_pos}}} | {{:<{largura_modo}}} | "
        f"{{:<{largura_workers}}} | {{:<{largura_chunksize}}} | "
        f"{{:>{largura_tempo}}} | {{:>{largura_taxa}}} |"
    )

    # Cria a linha de separação
    separador = (
        f"+-{'-'*largura_pos}-+-{'-'*largura_modo}-+-"
        f"{'-'*largura_workers}-+-{'-'*largura_chunksize}-+-"
        f"{'-'*largura_tempo}-+-{'-'*largura_taxa}-+"
    )

    # Imprime o cabeçalho
    print(separador)
    print(formato_linha.format("Posição", "Modo de Execução", "Workers", "Chunksize", "Tempo (s)", "Taxa (it/s)"    ))
    print(separador)

    # Imprime os dados
    for i, linha in enumerate(dados):
        print(formato_linha.format(
            f"{i + 1}º",
            linha['modo'],
            linha['workers'],
            linha['chunksize'],
            f"{linha['tempo']:.4f}",
            f"{linha['rate']:.2f}"
        ))

    print(separador)

# -----------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL (REESTRUTURADA PARA GERIR SESSÕES)
# -----------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulador de teste de força de senha para ficheiros .zip e .rar.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Grupo para iniciar um novo ataque
    new_attack_group = parser.add_argument_group('Novo Ataque', 'Argumentos para iniciar uma nova busca')
    new_attack_group.add_argument("arquivo", nargs='?', help="O caminho para o ficheiro .zip ou .rar.")
    new_attack_group.add_argument("-min", "--min_len", type=int, default=1, help="Comprimento mínimo da senha.")
    new_attack_group.add_argument("-max", "--max_len", type=int, default=8, help="Comprimento máximo da senha.")
    new_attack_group.add_argument("-d", "--digitos", action="store_true", help="Incluir dígitos (0-9).")
    new_attack_group.add_argument("-l", "--lowercase", action="store_true", help="Incluir letras minúsculas (a-z).")
    new_attack_group.add_argument("-u", "--uppercase", action="store_true", help="Incluir letras maiúsculas (A-Z).")
    new_attack_group.add_argument("-w", "--letters", action="store_true", help="Incluir letras case insensitive (a-zA-Z).")
    new_attack_group.add_argument("-s", "--simbolos", action="store_true", help="Incluir símbolos.")
    new_attack_group.add_argument("-a", "--alphanum", action="store_true", help="Atalho para letras e dígitos.")

    # Argumentos gerais
    new_attack_group.add_argument("-m", "--multithread", action="store_true", help="Ativar modo paralelo com múltiplos processos.")
    new_attack_group.add_argument("--workers", type=int, default=os.cpu_count(), help=f"Número de processos a serem utilizados (padrão: {os.cpu_count()}).")
    ## NOVO: Argumento para definir o laço inicial.
    new_attack_group.add_argument("--step", type=int, default=0, help="Número do laço (iteração) para iniciar o teste. Aplica-se ao primeiro comprimento do intervalo.")

    # Grupo para continuar um ataque
    continue_group = parser.add_argument_group('Continuar Ataque', 'Argumentos para continuar uma busca existente')
    continue_group.add_argument("--continue", dest='continue_file', nargs='?', const=True, help="Continue a última sessão para o ARQUIVO especificado.")

    # Argumentos comuns
    parser.add_argument("--session-file", default="cracker_sessions.json", help="Ficheiro para guardar as sessões.")
    parser.add_argument("--benchmark", action="store_true", help="Testa o desempenho desse processo, no modo sequencial e multi thread, arquivo .zip.")
    parser.add_argument("--benchmark-rar", action="store_true", help="Testa o desempenho desse processo, no modo sequencial e multi thread, arquivo .rar.")
    parser.add_argument("--test-method", choices=['lib', 'subprocess'], default='lib', help="Método para testar arquivos entre lib (pode ter falso positivos com .rar) e subprocess (geralmente mais lento) (padrão: lib).")

    args = parser.parse_args()
    session_manager = SessionManager(args.session_file)
    session_data = None
    target_file = args.arquivo or (args.continue_file if isinstance(args.continue_file, str) else None)

    if args.test_method == 'subprocess':
        global RAR_METHOD_TEST, ZIP_METHOD_TEST
        RAR_METHOD_TEST = 'subprocess'
        ZIP_METHOD_TEST = 'subprocess'

    # For test execution only
    if args.benchmark or args.benchmark_rar:
        target_path = target_file or None
        benchmark(args, target_path)
        return

    if args.min_len < 1 or args.max_len < args.min_len:
        print("[ERRO] Valores inválidos para comprimento mínimo/máximo.")
        return

    if args.workers < 2:
        print("[ERRO] O número de processos deve ser pelo menos 2.")
        return

    char_set = set()
    if args.alphanum: char_set.update(list(string.ascii_letters + string.digits))
    if args.digitos: char_set.update(list(string.digits))
    if args.lowercase: char_set.update(list(string.ascii_lowercase))
    if args.uppercase: char_set.update(list(string.ascii_uppercase))
    if args.letters: char_set.update(list(string.ascii_letters))
    if args.simbolos: char_set.update(list(string.punctuation))
    if not char_set:
        char_set.update(list(string.ascii_letters + string.digits + string.punctuation))
    charset = "".join(sorted(list(char_set)))

    # Best default chunksize for most scenarios
    chunksize = 2

    if args.continue_file:
        if not target_file:
            parser.error("O argumento --continue requer que o 'arquivo' seja especificado.")

        print(f"Procurando sessão para continuar para '{target_file}'...")
        session_data = session_manager.get_session(target_file)

        if not session_data:
            print("[ERRO] Nenhuma sessão encontrada para este arquivo. Inicie um novo ataque.")
            return

        if session_data['status'] == 'found':
            print(f"[INFO] A senha para este arquivo já foi encontrada: {session_data['found_password']}")
            return

        if session_data['status'] == 'no_password_needed':
            print(f"[INFO] Este arquivo não requer senha.")
            return

        print("Sessão encontrada. Retomando com os parâmetros guardados...")

        # Recria o charset a partir dos argumentos guardados
        s_args = session_data['charset_args']
        char_set = set()
        if s_args.get('alphanum'): char_set.update(list(string.ascii_letters + string.digits))
        if s_args.get('digits'): char_set.update(list(string.digits))
        if s_args.get('lowercase'): char_set.update(list(string.ascii_lowercase))
        if s_args.get('uppercase'): char_set.update(list(string.ascii_uppercase))
        if s_args.get('letters'): char_set.update(list(string.ascii_letters))
        if s_args.get('symbols'): char_set.update(list(string.punctuation))
        session_data['charset'] = "".join(sorted(list(char_set)))

    else: # Novo ataque
        if not target_file:
            parser.error("O argumento 'arquivo' é obrigatório para um novo ataque.")

        existing_session = session_manager.get_session(target_file)

        if existing_session:

            if existing_session['status'] == 'found':
                print(f"[INFO] A senha para este arquivo já foi encontrada: {existing_session['found_password']}")
                return

            if existing_session['status'] == 'no_password_needed':
                print(f"[INFO] Este arquivo não requer senha.")
                return

            if existing_session['status'] == 'running':
                choice = input(f"Sessão 'running' encontrada para este arquivo (última atualização: {existing_session['last_update']}).\nDeseja [c]ontinuar, [s]obrescrever ou [a]bortar? ").lower()
                if choice == 'c':
                    # Reutiliza a lógica de continuar
                    session_data = existing_session
                    print("Retomando sessão existente...")
                elif choice == 's':
                    print("Sobrescrevendo sessão existente...")
                else:
                    print("Operação abortada.")
                    return

        if not session_data: # Se não escolheu 'c' ou não havia sessão
            print("Iniciando nova sessão...")
            # Define o tipo de ficheiro
            file_type = None
            if target_file.lower().endswith('.zip'):
                file_type = 'zip'
            elif target_file.lower().endswith('.rar'):
                file_type = 'rar'
            else:
                print(f"[ERRO] Formato de ficheiro não suportado: '{file_path}'. Use .zip ou .rar.")
                return

            if not os.path.exists(target_file):
                print(f"[ERRO] O ficheiro '{target_file}' não foi encontrado.")
                return

            # Constrói o charset a partir dos argumentos
            char_set = set()
            if args.alphanum: char_set.update(list(string.ascii_letters + string.digits))
            if args.digitos: char_set.update(list(string.digits))
            if args.lowercase: char_set.update(list(string.ascii_lowercase))
            if args.uppercase: char_set.update(list(string.ascii_uppercase))
            if args.letters: char_set.update(list(string.ascii_letters))
            if args.simbolos: char_set.update(list(string.punctuation))
            if not char_set: # Padrão
                print("Nenhum conjunto de caracteres especificado. Usando alfanumérico + símbolos por padrão.")
                char_set.update(list(string.ascii_letters + string.digits + string.punctuation))
            charset = "".join(sorted(list(char_set)))

            # Cria a nova estrutura de dados da sessão
            session_data = {
                "target_file": os.path.abspath(target_file),
                "file_type": file_type,
                "charset_args": {
                    "digits": args.digitos,
                    "letters": args.letters,
                    "lowercase": args.lowercase,
                    "uppercase": args.uppercase,
                    "symbols": args.simbolos,
                    "alphanum": args.alphanum
                },
                "charset": charset,
                "min_len": args.min_len,
                "max_len": args.max_len,
                "current_len": args.min_len,
                "last_step": args.step,
                "status": "running",
                "found_password": None,
                "last_password": None,
                "last_update": datetime.now().isoformat()
            }
            session_manager.update_session(target_file, session_data)
            print("Nova sessão criada.")

    # Execução
    print("-" * 50)
    print(f"CPU Count: {multiprocessing.cpu_count()}")
    print(f"Alvo: {session_data['target_file']} (Tipo: {session_data['file_type']})")
    print(f"Charset: '{session_data['charset'][:40]}...' ({len(session_data['charset'])} caracteres)")
    print(f"Comprimento: de {session_data['min_len']} a {session_data['max_len']}")
    print("-" * 50)

    if args.multithread:
        # testar_senha_paralelo(file_path, file_type, args.min_len, args.max_len, charset, args.workers, args.step, chunksize)
        testar_senha_paralelo(session_manager, session_data, args.workers, chunksize)
    else:
        # testar_senha_sequencial(file_path, file_type, args.min_len, args.max_len, charset, args.step)
        testar_senha_sequencial(session_manager, session_data)

if __name__ == "__main__":
    try:
        multiprocessing.freeze_support()
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Execução interrompida pelo usuário. Encerrando...")
        try:
            exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as e:
        print(f"\n[ERRO FATAL] Ocorreu um erro inesperado: {e}")
