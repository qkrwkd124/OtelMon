# -*- coding: utf-8 -*-
import os
import json
import subprocess

originalFlowFile = session.get()
if originalFlowFile != None:
    # Process Count를 사용하기
    # 파이프라인의 키가 되는 속성 추가하기 (filename 같은거)

    # flow 파라미터 Get
    params = originalFlowFile.getAttributes()
    params_dict = dict(params)
    params_json = json.dumps(params_dict, indent=2)

    # Execute 스크립트에 저장된 Python 프로세스 파일명
    python_script = context.getProperty("Python Script File").evaluateAttributeExpressions(originalFlowFile).getValue()
    process_name = os.path.basename(python_script)

    # 시작 로그 작성
    log.info("[%s] [start] : python3 %s\n%s" %(process_name, python_script, params_json))

    #python3로 Python 파일 호출
    process = subprocess.Popen(
        ["python3", python_script], 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate(input=params_json)
    if stderr:
        log.error(stderr.decode("utf-8"))
    if process.returncode == 0:
        process_result = json.loads(stdout.decode('utf-8'))

        metric = process_result["metric"]
        
        session.putAttribute(originalFlowFile, "LAST_PROCESS", process_name)
        if process_result["metric"]["status"] == "success":
            process_status = REL_SUCCESS
        else:
            process_status = REL_FAILURE

        if len(process_result["items"]) != 0:
            for item in process_result["items"]:
                flowFile = session.create(originalFlowFile)

                log.debug(str(item["result"]))
                for key, value in item["result"].items() :
                    session.putAttribute(flowFile, key, unicode(value))
                
                # Metric 정보 추가
                metric["process_count"] = item["process_count"]
                session.putAttribute(flowFile, process_name, json.dumps(metric))

                # FlowFile 처리
                session.transfer(flowFile, process_status)
                log.info("[%s] [%s] : %s" %(process_name, process_result["metric"]["status"], json.dumps(metric)))

            # 원본 FlowFile 삭제
            session.remove(originalFlowFile)
                
        else:
            # 결과가 없는 프로세스
            # Metric 정보 추가
            metric["process_count"] = 0
            session.putAttribute(originalFlowFile, process_name, json.dumps(metric))

            # FlowFile 처리
            session.transfer(originalFlowFile, process_status)
            log.info("[%s] [%s] : %s" %(process_name, process_result["metric"]["status"], json.dumps(metric)))
        log.info("[%s] [%s] : %s" %(process_name, "end", "success"))

    else:
        # 비정상 종료
        log.error("[%s] [%s] : %s" %(process_name, "error", stderr.decode('utf-8')))
        session.transfer(originalFlowFile, REL_FAILURE)