# NVDAMacroManager (IDE moderno de macros e motor de automatização)

**Programador:** Muhammet Enes Şenovalı
**Versão:** 1.2.4

O NVDA Macro Manager é um gravador, editor e motor de reprodução acessível de macros de teclado, integrado com o leitor de ecrã NVDA. Destina-se a fluxos de trabalho repetíveis nos quais são conhecidas a aplicação de destino e a sequência de teclas gravada.

## 🚀 Funcionalidades principais

* **Dois modos de gravação (em direto e seguro):** No modo em direto, as teclas chegam às aplicações enquanto são gravadas. O modo seguro bloqueia as teclas físicas até ser interrompido com `NVDA + Windows + Shift + R`.
* **Atalhos dinâmicos do NVDA:** As macros guardadas são integradas no NVDA. Pode atribuir um atalho próprio a cada macro em `Preferências → Definir comandos → Gestor de macros`.
* **IDE profissional de macros (editor de eventos):**
  * **Fluxo linear:** As teclas e os atrasos são passos independentes (Esperar, Premir, Tecla premida, Tecla libertada).
  * **Área de transferência de eventos:** `Ctrl + C`, `Ctrl + X` e `Ctrl + V` copiam ou movem passos da macro.
  * **Anular/Refazer:** `Ctrl + Z` e `Ctrl + Y` anulam ou restauram alterações.
  * **Inserção de eventos:** Adicione novos atrasos ou teclas em qualquer ponto.
* **Captura inteligente de teclas:** Capture uma tecla física ou selecione-a numa lista localizada gerada pelo sistema operativo.
* **Reprodução de entrada do Windows:** A reprodução utiliza a API `SendInput` do Windows. Algumas aplicações protegidas, elevadas, remotas ou jogos podem rejeitar a entrada simulada; a compatibilidade com sistemas anti-cheat não é garantida.
* **Velocidade, atraso inicial e repetições:** Ajuste livremente a velocidade, escolha um atraso independente da velocidade antes do primeiro evento, utilize reprodução instantânea ou configure uma repetição infinita.
* **Bloqueio de aplicação:** Restrinja uma macro a uma aplicação. A reprodução não começa se não for possível confirmar a aplicação e é interrompida se o foco mudar.
* **Multilingue:** Catálogos de interface completos em inglês, turco, espanhol, alemão e português (Portugal).

## ⌨️ Atalhos predefinidos

* **`NVDA + Windows + R`:** Inicia ou interrompe a gravação em direto.
* **`NVDA + Windows + Shift + R`:** Inicia ou interrompe a gravação segura. As teclas físicas são bloqueadas durante a gravação.
* **`NVDA + Windows + P`:** Reproduz a última macro temporária gravada ou cancela uma reprodução em curso.
* **`NVDA + Shift + M`:** Abre o Gestor de macros.

## 📦 Instalação

1. Transfira o ficheiro `.nvda-addon` mais recente a partir de [GitHub Releases](https://github.com/m-enes-senovali/nvdaMacroManager/releases).
2. Abra o ficheiro enquanto o NVDA está em execução e confirme a instalação.
3. Reinicie o NVDA quando for solicitado e confirme o extra em **Menu do NVDA → Ferramentas → Loja de extras → Extras instalados**.

É necessário o NVDA 2023.1 ou posterior. Apenas o Windows é suportado, porque a gravação e a reprodução utilizam as APIs de teclado do Windows.

## 🛠️ Utilização

### 1. Gravar rapidamente uma macro

* Utilize `NVDA + Windows + R` para uma gravação normal.
* Utilize `NVDA + Windows + Shift + R` quando não pretender que as teclas produzam ações no sistema durante a gravação.
* Interrompa a gravação com o mesmo atalho e teste a macro temporária com `NVDA + Windows + P`.

### 2. Guardar e editar macros

Abra o gestor com `NVDA + Shift + M`, introduza um nome, configure a velocidade, o atraso inicial e o número de repetições e guarde a macro. O atraso inicial é aplicado uma única vez antes do primeiro evento e não é alterado pela velocidade de reprodução.

Selecione uma macro guardada e escolha **Editar**:

* Utilize `Shift` para selecionar vários eventos.
* Copie ou mova eventos com `Ctrl + C`, `Ctrl + X` e `Ctrl + V`.
* Altere atrasos ou teclas capturadas.
* Insira novos passos com **Adicionar evento**.

### 3. Atribuir atalhos personalizados

Abra `Preferências → Definir comandos` no NVDA, expanda **Gestor de macros**, selecione a macro e atribua-lhe um atalho.

## 🔒 Dados e segurança

As macros guardadas são armazenadas como `nvda_macros.json` no diretório de configuração ativo do NVDA. As atualizações são escritas de forma atómica e o ficheiro anterior é conservado como `nvda_macros.json.bak`. As importações de ficheiros e da área de transferência são validadas e limitadas por tamanho antes de serem utilizadas.

A gravação segura bloqueia as teclas físicas, mas a reprodução executa ações reais de teclado. Reveja as macros importadas, teste-as primeiro numa aplicação não crítica e utilize bloqueios de aplicação sempre que possível. O extra não pode contornar os níveis de integridade do Windows, aplicações protegidas, restrições de sessões remotas ou controlos de segurança de jogos.
