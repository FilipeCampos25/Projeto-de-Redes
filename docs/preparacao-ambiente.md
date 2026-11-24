# Preparação do ambiente — Issue #02

## Escopo e ordem de trabalho

Este manual prepara duas máquinas físicas ou virtuais para a [topologia HTTP/DNS](topologia.md). A executará futuramente `src/client.py`; B executará HTTP TCP/80 e DNS UDP/53. O Wireshark capturará na interface de B. GET `/`, POST `/echo` e a consulta DNS tipo A de `demo.lab.` diretamente a B são os fluxos planejados. Não alterar o DNS padrão do sistema.

1. Escolher A e B, identificar o sistema operacional e configurar uma rede autorizada que permita comunicação entre elas.
2. Registrar endereços, máscaras/prefixos, interfaces e modo de rede na topologia.
3. Preparar Python conforme o [README](../README.md), verificar conflitos locais de portas e revisar permissões.
4. Instalar e identificar a interface do Wireshark em B; realizar o teste ICMP controlado a partir de A.
5. Após as Issues #03 e #04, validar os serviços a partir de A. Após o cliente e a preparação da captura, confirmar os fluxos A/B e registrar evidências.

Os comandos de teste ativo e captura abaixo são instruções para execução manual no laboratório autorizado; não foram executados nesta entrega. Não usar NetProbe, varreduras de rede ou `localhost` para substituir a comunicação A/B. Os servidores e o cliente ainda não existem.

## 1. Escolher a rede e registrar as máquinas

Para máquinas físicas, usar uma LAN que permita comunicação entre os dois participantes. Para duas VMs no mesmo host, uma rede interna compartilhada ou host-only pode servir, desde que ambas estejam conectadas ao mesmo segmento. Para máquinas físicas e VMs, avaliar bridge na LAN autorizada. Redes internas/host-only de hosts diferentes não se conectam automaticamente.

NAT individual de cada VM pode permitir acesso externo sem permitir conexões de A para B. Confirmar a documentação do hipervisor e escolher uma rede compartilhada alcançável; não presumir que dois adaptadores chamados NAT pertençam ao mesmo segmento. Registrar o modo e o nome da rede virtual, mantendo acesso administrativo disponível antes de qualquer alteração manual.

Usar endereços fornecidos pelo DHCP ou atribuídos pelo administrador do laboratório. Não escolher IPs arbitrariamente. Anotar novamente os IPs antes da demonstração, pois concessões DHCP podem mudar. As máquinas devem ter endereços distintos. Na mesma sub-rede, a comunicação direta não depende de gateway; entre sub-redes, são necessárias rotas de ida e volta e autorização de rede.

## 2. Identificar IPv4, máscara, gateway e interface

Executar em **A e B** e transcrever os resultados na [topologia](topologia.md).

Windows, PowerShell:

```powershell
ipconfig
Get-NetIPAddress -AddressFamily IPv4 |
    Select-Object InterfaceAlias,InterfaceIndex,IPAddress,PrefixLength,AddressState
Get-NetIPConfiguration
```

`ipconfig` mostra IPv4, máscara e gateway por adaptador. `Get-NetIPAddress` associa o endereço ao nome/índice da interface e ao prefixo CIDR; `Get-NetIPConfiguration` complementa com o gateway. Se consultas CIM forem negadas, usar `ipconfig` e registrar a limitação, sem mudar permissões automaticamente.

Linux, Bash:

```bash
ip addr
ip -4 addr show
ip -4 route show
```

Em `inet`, o sufixo `/N` é o comprimento do prefixo da máscara; a rota `default via` identifica o gateway, quando existente, e `dev` indica a interface. Um prefixo `/24`, por exemplo, representa a máscara `255.255.255.0`; isso é uma equivalência, não uma atribuição para o laboratório.

Selecionar a interface conectada à rede compartilhada por A/B. Não usar loopback, adaptadores desconectados ou uma VPN sem relação com o laboratório. Um endereço link-local pode indicar ausência de DHCP; confirmar a configuração pretendida. Conferir se os endereços pertencem à mesma sub-rede conforme as máscaras, ou se existe roteamento autorizado. Havendo vários adaptadores, registrar qual rota alcança B e qual endereço de origem será usado.

Nos próximos comandos, `IP_A` e `IP_B` são **placeholders**, nunca nomes a descobrir automaticamente. Preencher as variáveis com os IPv4 reais já registrados, sem usar os endereços do ambiente Codex como padrão.

## 3. Verificar conectividade A → B

Em A, informar explicitamente o IPv4 confirmado de B. Manter a variável na mesma sessão de terminal para os testes posteriores.

Windows, PowerShell:

```powershell
$IP_B = Read-Host 'Digite o IPv4 confirmado da máquina B'
ping -4 -n 4 $IP_B
```

Linux, Bash:

```bash
read -r -p 'Digite o IPv4 confirmado da máquina B: ' IP_B
ping -4 -c 4 "$IP_B"
```

Respostas ICMP demonstram troca de pacotes com aquele destino naquele instante; não comprovam HTTP ou DNS. Timeout pode decorrer de filtragem ICMP, perda, endereço incorreto ou falta de rota. “Destino inacessível” exige verificar quem produziu a mensagem, a rota e o enlace. Registrar saída, perdas observadas, data e máquina de origem.

Se ICMP não responder, verificar IP/máscara, cabo/conexão, modo de rede das VMs e isolamento de clientes Wi-Fi (incluindo rede de convidados). Solicitar ao administrador uma rede de laboratório adequada, sem desabilitar proteções globais. **Não concluir que TCP falhou somente porque ping falhou.** Após o servidor HTTP existir e estar iniciado em B, testar TCP/80 a partir de A:

```powershell
# Windows: somente após Issue #03, na sessão com $IP_B definido
Test-NetConnection -ComputerName $IP_B -Port 80
```

`TcpTestSucceeded: True` confirma estabelecimento TCP; a resposta HTTP ainda deve ser verificada. `False` não distingue sozinho firewall, rota, serviço ausente ou bind incorreto. No Linux, o teste HTTP direcionado da seção seguinte também verifica o estabelecimento TCP. Não testar portas aleatórias.

## 4. Verificar portas e serviços

### Antes dos servidores: inspeção local em B

Windows, PowerShell:

```powershell
netstat -ano | findstr :80
netstat -ano | findstr :53
Get-NetTCPConnection -LocalPort 80 -State Listen -ErrorAction SilentlyContinue
Get-NetUDPEndpoint -LocalPort 53 -ErrorAction SilentlyContinue
```

As buscas com `findstr` são amplas: podem encontrar `:8080`, `:5353` ou a porta remota de uma conexão. Conferir **protocolo, endereço local e porta local exata**. Se um cmdlet falhar por permissão, isso não comprova porta livre; usar a saída de `netstat` ou registrar a pendência. Para identificar um PID observado, executar `Get-Process -Id NUMERO_DO_PID`, substituindo o placeholder pelo número real.

Linux, Bash:

```bash
ss -ltnp 'sport = :80'
ss -lunp 'sport = :53'
```

`ss` pertence ao conjunto iproute2; caso ausente, disponibilizá-lo pelo gerenciador da distribuição. Detalhes de processos de outros usuários podem exigir permissão administrativa. Para um PID observado, usar `ps -p NUMERO_DO_PID -o pid,user,comm,args`.

TCP em `LISTENING` (`LISTEN` no Linux) indica um socket aguardando conexões. UDP não possui handshake nem estado TCP `LISTENING`: um endpoint local associado à porta 53 (frequentemente `UNCONN` no `ss`) indica um socket UDP, sem comprovar que responde a DNS.

Um bind em loopback atende somente à própria máquina. Bind em `IP_B` atende à interface correspondente; `0.0.0.0` representa todas as interfaces IPv4 locais, não um endereço para o cliente usar. Uma linha IPv6 não comprova atendimento IPv4. Confirmar endereço, família e processo. Ausência de endpoint é apenas uma observação momentânea, não garantia de que o bind futuro terá êxito.

Se houver conflito, identificar o dono do serviço (por exemplo, servidor web ou resolvedor DNS) e combinar uma solução com o responsável, preferindo uma VM dedicada quando necessário. Não encerrar processos essenciais nem trocar as portas exigidas para mascarar o conflito. No Linux, bind abaixo de 1024 pode exigir privilégios/configuração do administrador; definir a forma de execução com ele, sem conceder capacidades ao interpretador Python global ou executar a interface gráfica do Wireshark como root por padrão.

### Após implementação: validação direcionada a B

Os testes abaixo são **pendentes das Issues #03/#04**. Iniciar os servidores conforme a documentação que acompanhar sua implementação e repetir a inspeção local. Em A, com `IP_B` já informado, conferir resposta HTTP:

```powershell
# Windows, se curl.exe estiver instalado
curl.exe --noproxy '*' --connect-timeout 5 --max-time 10 -i "http://${IP_B}/"
curl.exe --noproxy '*' --connect-timeout 5 --max-time 10 -i -H 'Content-Type: application/json' --data-binary '{}' "http://${IP_B}/echo"
nslookup -type=A demo.lab. $IP_B
```

```bash
# Linux, com curl e dig disponíveis
curl --noproxy '*' --connect-timeout 5 --max-time 10 -i "http://${IP_B}/"
curl --noproxy '*' --connect-timeout 5 --max-time 10 -i -H 'Content-Type: application/json' --data-binary '{}' "http://${IP_B}/echo"
dig @"$IP_B" demo.lab. A +notcp +ignore +time=2 +tries=1
```

`--data-binary` gera POST; `{}` é um corpo JSON mínimo sem dados pessoais. Conferir os códigos e o corpo com o contrato implementado: GET 200 e confirmação do POST são os resultados planejados. `--noproxy` mantém o acesso direto ao laboratório. Usar explicitamente `http://`, sem HTTPS. No Windows, `curl.exe` evita o alias `curl` de versões do PowerShell; verificar sua disponibilidade com `Get-Command curl.exe`.

No Linux, `dig` costuma ser fornecido por `dnsutils` (Debian/Ubuntu) ou `bind-utils` (Fedora); instalar somente se necessário. O teste apresentado evita TCP e fallback por truncamento. No Windows, `nslookup` informa o servidor consultado, mas sua saída sozinha não prova o transporte: confirmar consulta e resposta **UDP/53** na captura posterior. Nome do servidor mostrado como desconhecido por falta de resolução reversa não implica falha da consulta de `demo.lab.`. Conferir resposta A igual ao `IP_B` registrado. Não usar `Test-NetConnection -Port 53` como teste UDP, pois ele testa TCP.

## 5. Firewall e permissões do laboratório

Nenhuma regra é criada ou alterada por esta entrega. Primeiro verificar as políticas existentes com o administrador. Quando necessário, ele deverá permitir em B apenas entrada de **A (`IP_A`) para B (`IP_B`), TCP/80 e UDP/53**, no perfil/interface do laboratório; considerar também saída de A e tráfego de resposta conforme a política. As respostas usam como destino as portas efêmeras de A. ICMP, se autorizado, é uma liberação separada e não requisito para HTTP/DNS.

Não desabilitar o firewall nem expor os serviços à Internet. Registrar regra/identificador, máquina, direção, endereços, protocolo, porta, perfil/interface, justificativa, responsável e prazo de remoção. Definir antes do teste como remover **somente a regra temporária criada**; ao finalizar, encerrar serviços, reverter essa liberação e registrar a reversão. Não apagar regras preexistentes. Se o administrador não autorizar, registrar o impedimento e usar outro laboratório autorizado.

## 6. Wireshark em B

### Instalação e identificação

No Windows, baixar o instalador compatível no [site oficial](https://www.wireshark.org/download.html), instalar o Wireshark e o Npcap oferecido pelo instalador com a autorização administrativa aplicável. Npcap é necessário para captura ao vivo; abrir um arquivo salvo não comprova sua presença. Registrar as versões instaladas. Consulte a [instalação oficial no Windows](https://www.wireshark.org/docs/wsug_html_chunked/ChBuildInstallWinInstall.html).

No Linux, instalar pelo gerenciador da distribuição. Em Debian/Ubuntu, o procedimento é `sudo apt update` seguido de `sudo apt install wireshark`. Configurar a permissão de captura conforme a documentação do pacote (`/usr/share/doc/wireshark-common/README.Debian.gz` nessas distribuições), com o administrador, e abrir a interface como usuário comum. Outras distribuições têm nomes e procedimentos próprios. Consulte a [instalação oficial em Unix](https://www.wireshark.org/docs/wsug_html_chunked/ChBuildInstallUnixInstallBins.html). Instalação e permissões nas máquinas reais permanecem pendentes.

Em B, abrir **Capture → Options** (os nomes podem estar traduzidos) e associar o endereço `IP_B` à interface obtida no sistema. Registrar seu nome exato. Se B for VM, capturar dentro dela na interface ligada à rede A/B. Não escolher loopback ou uma interface apenas porque o gráfico mostra atividade. Nenhuma captura é necessária para transcrever o nome da interface; confirmar sua visibilidade exige o teste posterior.

### Captura e filtros previstos

Quando os serviços e o cliente existirem, iniciar servidores em B, iniciar a captura nessa interface, gerar GET/POST e DNS em A e parar a captura após o teste. Conferir pacotes de ida e volta com os IPv4 registrados e portas de origem/destino; selecionar mensagens HTTP e DNS para verificar método e nome consultado.

O **filtro de captura** limita o que será coletado, é definido antes de iniciar e usa sintaxe própria. Exemplo para as duas máquinas, substituindo os placeholders:

```text
host IP_A and host IP_B
```

O **filtro de exibição** seleciona o que aparece dentre os pacotes já capturados, sem removê-los do arquivo. Aplicar na barra de exibição, substituindo `IP_A` e `IP_B` pelos IPv4 reais:

```text
ip.addr == IP_A && ip.addr == IP_B
tcp.port == 80
udp.port == 53
http
dns
```

São alternativas de filtros, uma por vez. Para combinar, usar, por exemplo, `(ip.addr == IP_A && ip.addr == IP_B) && tcp.port == 80`. O filtro por IP mostra os dois sentidos; filtros por porta abrangem origem ou destino. `http` e `dns` dependem da decodificação, enquanto o filtro TCP inclui também handshake e ACK sem conteúdo HTTP. Não colar sintaxe de exibição no campo de captura. Referência: [filtros de captura](https://www.wireshark.org/docs/wsug_html_chunked/ChCapCaptureFilterSection).

### Perdas e evidências

Consultar **Statistics → Capture File Properties**, especialmente interfaces e contadores de descarte, quando fornecidos pelo driver. Registrar valor, intervalo, interface e disponibilidade da medição. Um contador indisponível deve ser anotado como **não informado**, nunca como zero. “Displayed” menor que “Captured” após aplicar filtro não significa perda de captura. Descartes no capturador também não equivalem, por si só, à perda ponta a ponta da rede. Referência: [propriedades da captura](https://www.wireshark.org/docs/wsug_html_chunked/ChStatSummary.html).

Salvar `.pcapng` e capturas de tela relevantes em `docs/evidencias/`, revisando o conteúdo antes de compartilhá-lo. O [README](../README.md) explica que capturas são ignoradas por padrão e como aprovar uma exceção específica. Cada evidência deve identificar teste, A/B, comando ou filtro, resultado, data com fuso e responsável. Não criar links para arquivos inexistentes. Registrar também versões do Wireshark/Npcap, se aplicável.

## 7. Problemas comuns

| Sintoma/causa | Verificação e ação manual |
|---|---|
| IP incorreto | Reconsultar o IPv4 em B, confirmar DHCP e corrigir a variável em A; não procurar outros hosts automaticamente. |
| Máscara ou sub-rede incorreta | Comparar prefixos e rede compartilhada; conferir rotas de ida/volta e solicitar correção ao administrador. |
| Porta ocupada | Identificar protocolo, porta local exata, endereço e PID; coordenar a solução sem desligar serviços essenciais. |
| Firewall bloqueando | Conferir bind e regra restrita A/B com o responsável; timeout isolado não identifica a causa. |
| Interface Wireshark errada | Comparar endereço e nome com a interface de B; repetir o teste controlado na interface correta. |
| VM em NAT inadequado | Confirmar alcance entre convidados/host; configurar rede compartilhada autorizada e registrar o modo. |
| Isolamento de clientes Wi-Fi | Verificar rede de convidados e política do ponto de acesso com o administrador; usar LAN apropriada. |
| Npcap indisponível | No Windows, verificar instalação/estado do driver e sua permissão; solicitar instalação ou reparo oficial. |
| Privilégios insuficientes | Distinguir erro de bind, captura e consulta administrativa; ajustar apenas a permissão necessária com o responsável. |
| Ping falha, HTTP funciona | Registrar ICMP bloqueado/indisponível e a evidência TCP/HTTP; não declarar falha geral de conectividade. |
| DNS sem resposta | Conferir servidor explícito B, bind UDP/53, nome consultado e firewall; validar transporte na captura. |

## 8. Diagnóstico local do workspace (não é validação de A/B)

Observações de **23/11/2026 (America/Sao_Paulo)**, responsável pela coleta: **Codex**. Apenas comandos locais de leitura foram executados. Nenhuma configuração, instalação, sondagem, ping ou captura foi realizada.

| Item | Evidência da consulta local | Limitação |
|---|---|---|
| Base Git | `HEAD` e `1_Estruturar-o-repositorio` apontavam para `dbc8280e476719e32f775413adb3b6157f84e8a3`; status inicial limpo | Branch atual: `Configurar_ambiente-Desenvolver_servidor_HTTP`; seu nome não amplia o escopo desta issue |
| Python | `python --version` e `py -3 --version`: Python 3.12.10 | Não comprova Python nas máquinas A/B |
| Sistema | `platform.platform()`: `Windows-11-10.0.26200-SP0`; `platform.machine()`: `AMD64` | Consulta `Get-CimInstance Win32_OperatingSystem` negada pelo ambiente |
| Rede local | `ipconfig` retornou adaptador `Ethernet`, IPv4, máscara e gateway | Valores locais não foram atribuídos a A/B nem reproduzidos como configuração do laboratório |
| Consultas de rede via CIM | `Get-NetIPAddress` e `Get-NetIPConfiguration`: acesso negado | Utilizado `ipconfig` como alternativa de leitura; sem elevar permissões |
| Ferramentas encontradas | `Get-Command` encontrou `python`, `py`, `ipconfig`, `ping`, `netstat`, `Test-NetConnection` e `nslookup` | Presença não significa execução ou conectividade comprovada |
| Wireshark/TShark | Não encontrados por `Get-Command`; `Test-Path 'C:\Program Files\Wireshark\Wireshark.exe'` retornou `False` | Não exclui instalação em outro local; operação não validada |
| Npcap | Consultas a `Get-Service -Name npcap` e ao caminho usual `C:\Windows\System32\drivers\npcap.sys` não retornaram item, com erros suprimidos | Evidência insuficiente para afirmar ausência; instalação e funcionamento pendentes |
| Aplicações | `src/` contém apenas `.gitkeep` | HTTP, DNS e cliente ainda não implementados |

Essas observações são um registro textual da sessão, não evidências de tráfego. Não houve inspeção de portas das máquinas reais, acesso a redes de integrantes ou execução do NetProbe. A rede local do workspace não foi sondada.

## 9. Matriz de validação do laboratório

| Teste | Resultado | Evidência | Responsável |
|---|---|---|---|
| Identificar IP_A | Pendente | — | — |
| Identificar IP_B | Pendente | — | — |
| Verificar conectividade | Pendente | — | — |
| Verificar TCP/80 | Pendente | — | — |
| Verificar UDP/53 | Pendente | — | — |
| Identificar interface de captura | Pendente | — | — |
| Confirmar tráfego A/B | Pendente | — | — |

Data da validação real: **pendente**. Responsável do laboratório: **pendente**. Atualizar somente com evidências efetivas, registrando em cada resultado a data, o comando/filtro e eventuais limitações. TCP/80 e UDP/53 exigem separar inspeção de conflitos antes da implementação de validação funcional após #03/#04. Confirmação completa de tráfego depende também do cliente e da captura (#05/#06).

**Status da Issue #02:** preparação documental entregue; configuração e validação real pendentes. A issue somente poderá ser concluída após comprovar a conectividade nas máquinas do laboratório, preencher a topologia e atender aos critérios do [checklist](../checklist.md).
