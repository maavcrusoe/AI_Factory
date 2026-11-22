select 'projects=' || (select count(*) from projects)
  || ' users=' || (select count(*) from users)
  || ' tokens=' || (select count(*) from developer_tokens)
  || ' items=' || (select count(*) from work_items)
  || ' events=' || (select count(*) from work_item_events)
  || ' states=' || coalesce(
       (select string_agg(s, ',' order by s) from (select status || ':' || count(*) as s from work_items group by status) x),
       '-');
