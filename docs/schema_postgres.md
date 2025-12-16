|Tabela|Coluna|Tipo de Dado|Tamanho Max|Aceita Null|Valor Padrão|
|------|------|------------|-----------|-----------|------------|
|categorias|id|integer||Não|nextval('categorias_id_seq'::regclass)|
|categorias|nome|character varying|50|Não||
|lista_itens|id|integer||Não|nextval('lista_itens_id_seq'::regclass)|
|lista_itens|produto_id|integer||Sim||
|lista_itens|quantidade|double precision||Não||
|lista_itens|unidade_id|integer||Sim||
|lista_itens|usuario|character varying|50|Sim||
|lista_itens|status|character varying|20|Sim||
|lista_itens|adicionado_em|timestamp without time zone||Sim||
|lista_itens|origem_input|character varying|100|Sim||
|produtos|id|integer||Não|nextval('produtos_id_seq'::regclass)|
|produtos|nome|character varying|100|Não||
|produtos|emoji|character varying|10|Sim||
|produtos|categoria_id|integer||Sim||
|produtos|unidade_padrao_id|integer||Sim||
|reminders|id|integer||Não|nextval('reminders_id_seq'::regclass)|
|reminders|google_id|character varying|100|Sim||
|reminders|calendar_id|character varying|100|Sim||
|reminders|parent_id|character varying|100|Sim||
|reminders|title|character varying|200|Não||
|reminders|notes|text||Sim||
|reminders|due_date|timestamp without time zone||Sim||
|reminders|status|character varying|20|Sim||
|reminders|usuario|character varying|50|Sim||
|reminders|updated_at|timestamp without time zone||Sim||
|tasks|id|integer||Não|nextval('tasks_id_seq'::regclass)|
|tasks|descricao|character varying|200|Não||
|tasks|responsavel|character varying|50|Sim||
|tasks|prioridade|integer||Sim||
|tasks|status|character varying|20|Sim||
|tasks|created_at|timestamp without time zone||Sim||
|unidades_medida|id|integer||Não|nextval('unidades_medida_id_seq'::regclass)|
|unidades_medida|nome|character varying|20|Não||
|unidades_medida|simbolo|character varying|5|Não||
|users|id|integer||Não|nextval('users_id_seq'::regclass)|
|users|username|character varying|80|Não||
|users|password_hash|character varying|256|Não||
|weather_cache|id|integer||Não|nextval('weather_cache_id_seq'::regclass)|
|weather_cache|city|character varying|50|Sim||
|weather_cache|data_json|text||Sim||
|weather_cache|last_updated|timestamp without time zone||Sim||
