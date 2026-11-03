# TALVOA — plano de implementação seguro (Issue #68)

**Responsável sugerido:** robô Desenvolvimento + revisão do robô Segurança  
**Estado:** proposta técnica em branch isolada; sem alterações no produto ou produção.

## Escopo técnico

1. Inventariar endpoints administrativos de impressoras, setores, custos e nomenclaturas que utilizam `company_id` implícito.
2. Introduzir contexto explícito de tenant para operações administrativas do perfil `platform_admin`, validando autorização no servidor.
3. Manter `client` estritamente somente leitura, inclusive no modo preview.
4. Registrar trilha de auditoria: ator, empresa-alvo, operação, data/hora e resultado.
5. Cobrir tentativas de acesso e mutação entre tenants com testes negativos.

## Critérios de aceite

- [ ] Nenhuma mutação administrativa sem empresa-alvo explícita.
- [ ] Um usuário `client` não consegue modificar dados por chamadas diretas à API.
- [ ] O `platform_admin` só opera sobre a empresa-alvo autorizada.
- [ ] Auditoria registra o ator e o tenant de cada alteração.
- [ ] Testes automatizados validam cenários permitidos e bloqueados.
- [ ] Revisão humana do PR concluída antes de merge ou deploy.

## Guardrails

Não executar migrações, não alterar banco de produção, não publicar credenciais e não realizar deploy automático. Esta entrega é um plano revisável, **não uma correção implementada**.

Fonte: https://github.com/GENESIS-Technology-BR/printflow-ai/issues/68
