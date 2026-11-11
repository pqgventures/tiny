# Tiny plugin e Tiny World: estado em 11/11/2026

## Plugin (pronto para o post)
- main = v0.2.5 (correção de túneis do PR #1). Instalação limpa pelo GitHub testada em 11/11: base da Praça da Liberdade (BH) em 43 s, 7/7 quadros pintados pelo paint.sh, nenhum para repintar.
- A pintura hoje levou de 1 a 13 min por quadro (rede e geração de imagem lentas); em 08/11 foi 1 min por quadro.
- O main não menciona o Tiny World.

## Tiny World (no ar, sem anúncio)
- Mapa: https://tiny-world.agenturl.dev (cópia estática; o servidor republica a cada mudança). API, páginas de cidade e imagens: https://tiny-world-production-2283af47.up.railway.app (Railway, projeto tiny-cities, serviço tiny-world, volume /data).
- Código do servidor: tiny-cities/tiny-world (sem git). Chave de admin: ~/.config/tiny-cities/tinyworld.key e Dock tiny-cities/producao/TINY_WORLD_ADMIN.
- Fila do Tiny SP: 744 quadros do bloco leste-a, bases no R2 em tw-jobs/sao-paulo/leste-a/ (seed_sp_r2.py). 1 quadro de teste aceito no ar.
- Cliente: branch tiny-cities-hub (PR #2, rascunho): hub.py, paint_api.py, manifesto do Claude Code, download do OpenStreetMap em paralelo.

## Falta, em ordem
1. Merge do PR #2: sem ele o llms.txt manda clonar um repositório que não tem hub.py. O download em paralelo do OpenStreetMap ainda não foi visto funcionando com os servidores no ar.
2. Chat "Tiny SP · expansão" puxar os aceitos: GET /api/jobs/inbox?city=sao-paulo (cabeçalho X-Admin-Key), passar pelo portão do bloco, costurar, e avisar com POST /api/admin/tiles {city, pulled, on_map, drop}. Sem isso ninguém passa de "Accepted" para "On the map". Não foi combinado ainda.
3. Página de crédito /me/<id> e link "veja no mapa": escritos, sem teste no ar.
4. Uma pessoa de fora (ou um agente Claude limpo) fazer o fluxo inteiro pelo llms.txt.
5. No Tiny SP: botão "Help paint" e créditos (patch para a expansão publicar).
6. Raio das cidades inteiras é chute (SP 22 km, BCN 11 km); cidade da comunidade ainda não encaixa lugares vizinhos.
