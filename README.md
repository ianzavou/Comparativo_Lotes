# Comparativo de Roteirização VV

Dashboard e relatório para comparar a estrutura espacial das rotas atuais com os agrupamentos otimizados, sempre dentro do mesmo lote e sem relacionar diretamente os IDs das ULs.

## Uso diário

1. Mantenha os arquivos `Rotas_Atuais_VV_Completo.xlsx` e `Rota_Pronta_VV_Consolidado.xlsx` nesta pasta.
2. Acrescente e salve as novas linhas no arquivo otimizado.
3. Para atualizar o dashboard e o relatório Excel, abra `analise_rotas.ipynb` e execute **Run All**.
4. O Streamlit apenas lê os resultados já processados em `outputs/dashboard_snapshot.pkl.gz`. Após o **Run All**, atualize a página do navegador.
5. Para atualizar a versão online, execute `publicar_dashboard.bat` depois do **Run All**.

O Excel final é salvo em `outputs/Comparativo_Rotas_VV.xlsx` e pode ser baixado pelo dashboard, sem recalcular os dados.

## Inicialização pelo Windows

- Dê duplo clique em `start_streamlit.bat` para usar o dashboard localmente em `http://localhost:8503`.
- Para disponibilizá-lo pela internet, dê duplo clique em `start_ngrok.bat`. Se necessário, ele inicia o Streamlit automaticamente e aguarda a porta 8503 ficar disponível.
- O túnel ngrok usa a mesma política de autenticação do projeto `Notebook Ritmo Operacional`.
- O endereço público HTTPS é exibido na janela do ngrok. Fechar essa janela encerra o acesso externo.

## Publicação no Streamlit Community Cloud

O aplicativo online utiliza somente estes artefatos processados:

- `outputs/dashboard_snapshot.pkl.gz`, com os dados exibidos no dashboard;
- `outputs/Comparativo_Rotas_VV.xlsx`, disponibilizado para download.

As duas planilhas-fonte estão bloqueadas no `.gitignore` e não são enviadas pelo script de publicação. Como o snapshot contém instalações e coordenadas, use um repositório **privado** e mantenha o aplicativo **privado** no Streamlit Community Cloud.

### Primeira publicação

1. Crie um repositório **privado** e vazio no GitHub, sem adicionar README ou `.gitignore` pelo site.
2. Dê duplo clique em `configurar_github.bat` e informe seu nome, e-mail e a URL HTTPS do repositório. O navegador poderá abrir para autenticar o primeiro envio.
3. Entre em `share.streamlit.io`, clique em **Create app** e selecione o repositório, a branch principal e o arquivo `app.py`.
4. Em **Advanced settings**, selecione Python 3.13. Não cadastre as credenciais do ngrok em `Secrets` — este dashboard não precisa delas.
5. Após o deploy, em **Share**, autorize somente os e-mails que poderão acessar o aplicativo.

O Community Cloud escolhe endereço e porta automaticamente. A porta 8503 permanece configurada apenas nos arquivos `.bat` usados no Windows.

### Atualizações seguintes

1. Atualize `Rota_Pronta_VV_Consolidado.xlsx`.
2. Execute **Run All** em `analise_rotas.ipynb`.
3. Confirme que o dashboard local abre normalmente.
4. Dê duplo clique em `publicar_dashboard.bat`.

O script envia somente código, configuração, logo, snapshot e relatório final. A alteração no GitHub dispara o redeploy automático do Community Cloud.

## Regras da comparação

- As métricas espaciais utilizam todas as instalações disponíveis em cada cenário do lote.
- Estabilidade, retenção e fragmentação utilizam somente instalações presentes nos dois cenários do mesmo lote.
- As distâncias são Haversine e expressas em quilômetros.
- A aba `Percurso total` estima um caminho aberto por vizinho mais próximo em cada UL, nas visões Haversine e GeoPandas/UTM; o total do lote é a soma dessas ULs.
- Os dados não possuem sequência de visita ou rede viária; os resultados medem compactação e separação dos grupos, não distância rodada.
