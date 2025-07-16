SELECT 
    pe.id, 
    pe.host_name,
    pe.platform_type,
    pe.group_name,
    pe.process_name, 
    pe.error_message, 
    pe.error_type,
    pe.start_time, 
    pe.end_time, 
    pe.duration_seconds
FROM 
    process_executions pe
LEFT JOIN 
    alert_history ah ON pe.id = ah.process_execution_id
WHERE 
    pe.success = 'FAILED'
    AND pe.end_time > DATE_SUB(NOW(), INTERVAL 24 HOUR)
    AND ah.id IS NULL  -- 알람 이력이 없는 항목만 선택
ORDER BY 
    pe.end_time DESC