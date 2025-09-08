import os
import shutil
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

PRIMO = 104729          # tamanho da tabela (primo)
CHUNK = 1024 * 1024     # 1MB por leitura (comparação de conteúdo)

def comparar_arquivos(arquivo1, arquivo2):
    try:
        if os.path.getsize(arquivo1) != os.path.getsize(arquivo2):
            return False
        with open(arquivo1, 'rb') as f1, open(arquivo2, 'rb') as f2:
            while True:
                b1 = f1.read(CHUNK)
                b2 = f2.read(CHUNK)
                if b1 != b2:
                    return False
                if not b1:
                    return True
    except Exception:
        return False

class TabelaHash:
    def __init__(self, m=PRIMO):
        self.m = m
        self.vetor = [dict() for _ in range(m)]
        # Contadores mínimos
        self.comparacoes_tamanho_busca_total = 0   # 1 por arquivo ao consultar o bucket/ chave (tamanho)
        self.chaves_ocupadas = 0                  # tamanhos distintos inseridos (disponibilidade/ocupação)

    def _idx(self, tamanho):
        return tamanho % self.m

    def inserir(self, tamanho, caminho):
        b = self.vetor[self._idx(tamanho)]
        # Se for um tamanho novo neste bucket, conta como nova "chave" ocupada
        if tamanho not in b:
            self.chaves_ocupadas += 1
            b[tamanho] = [caminho]
        else:
            b[tamanho].append(caminho)

    def buscar_mesmo_tamanho(self, tamanho):
        # Análogo à comparação de "tamanho": contamos 1 por arquivo.
        self.comparacoes_tamanho_busca_total += 1
        b = self.vetor[self._idx(tamanho)]
        return b.get(tamanho, [])

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Verificador de duplicidade com Hashing")
        self.geometry("820x560")
        self.minsize(820, 560)

        self.dir_origem = tk.StringVar()
        self.dir_destino = tk.StringVar()
        self.worker_thread = None
        self.stop_flag = threading.Event()
        self.log_queue = queue.Queue()
        self.total_arquivos = 0

        self._build_ui()
        self._poll_log_queue()

    def _ui(self, fn, *args, **kwargs):
        self.after(0, lambda: fn(*args, **kwargs))

    def _set_progress(self, value, total):
        def _apply():
            self.progress.configure(maximum=max(total, 1), value=value)
            self.lbl_prog.config(text=f"{value} / {total} arquivos processados")
        self._ui(_apply)

    def _btn_states(self, start_state, stop_state):
        self._ui(self.btn_start.config, state=start_state)
        self._ui(self.btn_stop.config, state=stop_state)

    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}
        frm_top = ttk.LabelFrame(self, text="Pastas")
        frm_top.pack(fill="x", **pad)

        ttk.Label(frm_top, text="Origem:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(frm_top, textvariable=self.dir_origem).grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(frm_top, text="Escolher…", command=self._escolher_origem).grid(row=0, column=2, padx=6, pady=6)

        ttk.Label(frm_top, text="Destino:").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(frm_top, textvariable=self.dir_destino).grid(row=1, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(frm_top, text="Escolher…", command=self._escolher_destino).grid(row=1, column=2, padx=6, pady=6)

        frm_top.columnconfigure(1, weight=1)

        frm_ctrl = ttk.Frame(self)
        frm_ctrl.pack(fill="x", **pad)
        self.btn_start = ttk.Button(frm_ctrl, text="Iniciar", command=self._iniciar)
        self.btn_start.pack(side="left", padx=6)
        self.btn_stop = ttk.Button(frm_ctrl, text="Parar", command=self._parar, state="disabled")
        self.btn_stop.pack(side="left")
        ttk.Button(frm_ctrl, text="Salvar log…", command=self._salvar_log).pack(side="right")

        frm_prog = ttk.Frame(self)
        frm_prog.pack(fill="x", **pad)
        self.lbl_prog = ttk.Label(frm_prog, text="Pronto.")
        self.lbl_prog.pack(side="left")
        self.progress = ttk.Progressbar(frm_prog, mode="determinate", maximum=100)
        self.progress.pack(side="right", fill="x", expand=True, padx=6)

        frm_log = ttk.LabelFrame(self, text="Saída / Log")
        frm_log.pack(fill="both", expand=True, **pad)
        self.txt_log = tk.Text(frm_log, wrap="word", height=22, state="disabled")
        self.txt_log.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(frm_log, command=self.txt_log.yview)
        scroll.pack(side="right", fill="y")
        self.txt_log.configure(yscrollcommand=scroll.set)

        ttk.Label(self, text="Dica: escolha uma pasta de origem com muitos arquivos e uma de destino vazia.").pack(fill="x", padx=8, pady=(0, 10))

    def _escolher_origem(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta de origem")
        if caminho: self.dir_origem.set(caminho)

    def _escolher_destino(self):
        caminho = filedialog.askdirectory(title="Selecione a pasta de destino")
        if caminho: self.dir_destino.set(caminho)

    def _iniciar(self):
        origem = self.dir_origem.get().strip()
        destino = self.dir_destino.get().strip()
        if not origem or not os.path.isdir(origem):
            messagebox.showerror("Erro", "Selecione uma pasta de origem válida.")
            return
        if not destino:
            messagebox.showerror("Erro", "Selecione uma pasta de destino.")
            return
        if os.path.abspath(origem) == os.path.abspath(destino):
            messagebox.showerror("Erro", "Origem e destino não podem ser a mesma pasta.")
            return

        os.makedirs(destino, exist_ok=True)

        # Reset
        self._clear_log()
        self.stop_flag.clear()
        self._btn_states("disabled", "normal")
        self._log(f"Procurando arquivos em: {origem} (hash primo, sem ordenação)")
        self._log("=" * 60)

        self.total_arquivos = self._contar_arquivos(origem)
        self._set_progress(0, self.total_arquivos)

        self.worker_thread = threading.Thread(target=self._deduplicar_worker, args=(origem, destino), daemon=True)
        self.worker_thread.start()

    def _parar(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.stop_flag.set()
            self._log("Solicitada parada. Aguarde finalizar o arquivo atual…")

    def _salvar_log(self):
        conteudo = self.txt_log.get("1.0", "end-1c")
        if not conteudo.strip():
            messagebox.showinfo("Salvar log", "O log está vazio.")
            return
        caminho = filedialog.asksaveasfilename(title="Salvar log", defaultextension=".txt",
                                               filetypes=[("Texto", "*.txt"), ("Todos os arquivos", "*.*")])
        if caminho:
            try:
                with open(caminho, "w", encoding="utf-8") as f:
                    f.write(conteudo)
                messagebox.showinfo("Salvar log", f"Log salvo em:\n{caminho}")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível salvar o log:\n{e}")

    def _deduplicar_worker(self, dir_origem, dir_destino):
        tabela = TabelaHash(m=PRIMO)

        total_arquivos = 0
        arquivos_copiados = 0
        duplicatas = 0
        processados = 0

        comparacoes_byte = 0  # comparações de conteúdo (byte-a-byte)
        start_time = time.time()

        # Loga disponibilidade inicial (0 ocupadas)
        self._log(f"Disponibilidade do hash: chaves ocupadas = {tabela.chaves_ocupadas} / {tabela.m} "
                  f"({tabela.chaves_ocupadas / tabela.m:.4f} de fator de carga)")

        try:
            for pasta_atual, _, arquivos in os.walk(dir_origem):
                for nome_arquivo in arquivos:
                    if self.stop_flag.is_set():
                        raise KeyboardInterrupt

                    caminho_completo = os.path.join(pasta_atual, nome_arquivo)
                    try:
                        tamanho = os.path.getsize(caminho_completo)
                    except Exception:
                        continue

                    total_arquivos += 1
                    duplicado = False

                    # Busca no hash: conta UMA comparação de tamanho por arquivo
                    candidatos = tabela.buscar_mesmo_tamanho(tamanho)

                    if candidatos:
                        for candidato in candidatos:
                            comparacoes_byte += 1
                            if comparar_arquivos(caminho_completo, candidato):
                                self._log(f"ARQUIVO DUPLICADO: {nome_arquivo} (igual a {os.path.basename(candidato)})")
                                duplicatas += 1
                                duplicado = True
                                break

                    if not duplicado:
                        destino_final = os.path.join(dir_destino, nome_arquivo)
                        contador = 1
                        while os.path.exists(destino_final):
                            base, ext = os.path.splitext(nome_arquivo)
                            destino_final = os.path.join(dir_destino, f"{base}_{contador}{ext}")
                            contador += 1

                        try:
                            shutil.copy2(caminho_completo, destino_final)
                        except Exception as e:
                            self._log(f"ERRO ao copiar '{nome_arquivo}': {e}")
                        else:
                            tabela.inserir(tamanho, destino_final)
                            arquivos_copiados += 1
                            # opcional: remover log de cópia para reduzir ruído
                            self._log(f"COPIADO: {nome_arquivo} ({tamanho} bytes)")

                    processados += 1
                    if (processados % 25 == 0) or (processados == self.total_arquivos):
                        self._set_progress(processados, self.total_arquivos)

            duracao_total = time.time() - start_time


            media_tamanho_por_arquivo = tabela.comparacoes_tamanho_busca_total / max(total_arquivos, 1)
            media_byte_por_arquivo = comparacoes_byte / max(total_arquivos, 1)


            fator_carga = tabela.chaves_ocupadas / tabela.m

            self._log("=" * 60)
            self._log("RESULTADO:")
            self._log(f"Total de arquivos encontrados: {total_arquivos}")
            self._log(f"Arquivos únicos copiados: {arquivos_copiados}")
            self._log(f"Arquivos duplicados: {duplicatas}")
            self._log(f"Pasta destino: {dir_destino}")
            self._log("")
            self._log("DISPONIBILIDADE DO HASH:")
            self._log(f"Chaves ocupadas (tamanhos distintos): {tabela.chaves_ocupadas} / {tabela.m} "
                      f"({fator_carga:.4f} de fator de carga)")
            self._log("")
            self._log("DESEMPENHO:")
            self._log(f"Comparações de TAMANHO (busca hash) - total: {tabela.comparacoes_tamanho_busca_total}")
            self._log(f"Média de comparações de TAMANHO por arquivo: {media_tamanho_por_arquivo:.2f}")
            self._log(f"Comparações de conteúdo (byte-a-byte) - total: {media_byte_por_arquivo * total_arquivos:.0f}")
            self._log(f"Média de comparações de conteúdo por arquivo: {media_byte_por_arquivo:.2f}")
            self._log(f"Tempo total: {duracao_total:.4f} s")

        except Exception as e:
            self._log(f"[ERRO] {type(e).__name__}: {e}")
        finally:
            self._btn_states("normal", "disabled")
            self.worker_thread = None

    def _contar_arquivos(self, raiz):
        return sum(len(arquivos) for _, _, arquivos in os.walk(raiz))

    def _log(self, msg):
        self.log_queue.put(str(msg))

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_text(msg + "\n")
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    def _append_text(self, text):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", text)
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _clear_log(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")

if __name__ == "__main__":
    App().mainloop()
