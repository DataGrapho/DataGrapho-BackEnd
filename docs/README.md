# DataGrapho-Infra

Repositório criado para armazenar e centralizar o CI/CD do projeto.

## Organização de Branches

feature/exemplo-issue ---Pull Request (1)---> infra/pipeline-frontend

## Fluxo da Pipeline

![diagrama-pipeline-frontend](./docs/diagrama-frontend.jpg)

### Primeiro Fluxo (feature/*)
1. Desenvolvedor efetua push para uma branch `feature/*`
2. Orquestrador do CI inicia o workflow
3. Build padrão do Node inicia através do `ci-vue.yaml`
4. Ao buildar com sucesso, inicia-se o `ci-code-scan.yaml`, efetuando validações de qualidade e SAST com SonarQube e Semgrep, ambos em paralelo.

### Segundo Fluxo (release/*)
1. Desenvolvedor formaliza Pull Request de uma branch `develop` para uma branch `release/*`
2. Orquestrador do CI inicia o workflow
3. Build padrão do Node inicia através do `ci-vue.yaml`
4. Ao buildar com sucesso, inicia-se o `ci-code-scan.yaml`, efetuando validações de qualidade e SAST com SonarQube e Semgrep, ambos em paralelo.
5. Ao passar pelas validações de code scan, inicia-se o `ci-build.yaml`, efetuando o build/push de uma imagem Docker, assim como um scan de vulnerabilidades da imagem através do Trivy.

### Terceiro Fluxo (main)
1. Desenvolvedor formaliza Pull Request de uma branch `develop` para uma branch `release/*`
2. Orquestrador do CI inicia o workflow
3. Build padrão do Node inicia através do `ci-vue.yaml`
4. Ao buildar com sucesso, inicia-se o `ci-code-scan.yaml`, efetuando validações de qualidade e SAST com SonarQube e Semgrep, ambos em paralelo.
5. Ao passar pelas validações de code scan, inicia-se o `ci-build.yaml`, efetuando o build/push de uma imagem Docker, assim como um scan de vulnerabilidades da imagem através do Trivy.
6. Ao passar pela validação de vulnerabilidade da imagem, inicia-se o `cd-deploy.yaml`, efetuando o deploy da imagem no servidor dedicado hospedado no Proxmox.
7. Ao executar o deploy com sucesso, o workflow detecta qual `release/*` gerou esta nova imagem, e inicia o `version-tag.yaml`, aplicando assim uma `Git Tag` na `main` com a versão daquela release.
```txt
Exemplo:
Pull Request #2 (Closed)
main <- release/1.2.3

git tag -a v1.2.3 -m "versão v1.2.3"
```