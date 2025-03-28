import smtplib
from email.message import EmailMessage
import requests
from typing import Dict, Any

import logging
from logger import get_logger

# logger = logging.getLogger(__name__)
logger = get_logger(__name__)

class NotificationService:
    def __init__(self, config):
        self.config = config
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.smtp_user = config.SMTP_USER
        self.smtp_password = config.SMTP_PASSWORD
        self.sms_api_key = config.SMS_API_KEY
        self.sms_api_url = config.SMS_API_URL
        self.admin_emails = config.ADMIN_EMAILS
        self.admin_phones = config.ADMIN_PHONES
        
        logger.info(f"알림 서비스 초기화됨: SMTP 서버={self.smtp_server}, 포트={self.smtp_port}")
    
    async def send_email_alert(self, execution_data: Dict[str, Any]):
        """실패한 프로세스에 대한 이메일 알림 전송"""
        if not execution_data.get("error_message"):
            return
            
        msg = EmailMessage()
        msg['Subject'] = f"[ETL 오류 알림] {execution_data['platform_type']} - {execution_data['group_name']} - {execution_data['process_name']}"
        msg['From'] = self.smtp_user
        msg['To'] = ", ".join(self.admin_emails)
        
        body = f"""
        ETL 프로세스 실행 오류가 발생했습니다.
        
        서버: {execution_data['host_name']}
        플랫폼: {execution_data['platform_type']}
        그룹: {execution_data['group_name']}
        프로세스: {execution_data['process_name']}
        시작 시간: {execution_data['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
        종료 시간: {execution_data['end_time'].strftime('%Y-%m-%d %H:%M:%S')}
        실행 시간: {execution_data['duration_seconds']:.2f}초
        
        오류 유형: {execution_data['error_type']}
        오류 메시지: {execution_data['error_message']}
        """
        logger.info(f"이메일 내용: {body}")
        msg.set_content(body)
        
        try:
            logger.debug(f"SMTP 서버 연결 시도: {self.smtp_server}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                logger.debug("SMTP TLS 연결 설정")
                server.starttls()
                logger.debug(f"SMTP 로그인 시도: {self.smtp_user}")
                server.login(self.smtp_user, self.smtp_password)
                logger.debug(f"이메일 전송 중: 수신자={self.admin_emails}")
                server.send_message(msg)
        except Exception as e:
            logger.error(f"이메일 전송 실패: {str(e)}", exc_info=True)
            logger.debug(f"이메일 내용: {body}")
    
    async def send_sms_alert(self, execution_data: Dict[str, Any]):
        """실패한 프로세스에 대한 SMS 알림 전송"""
        if not execution_data.get("error_message"):
            return
            
        message = (f"ETL 오류: {execution_data['platform_type']}-{execution_data['group_name']}"
                  f"-{execution_data['process_name']} / {execution_data['error_type']}")
        
        for phone in self.admin_phones:
            try:
                payload = {
                    "api_key": self.sms_api_key,
                    "to": phone,
                    "message": message
                }
                requests.post(self.sms_api_url, json=payload)
            except Exception as e:
                logger.error(f"Failed to send SMS: {str(e)}")
    
    async def notify_failure(self, execution_data: Dict[str, Any]):
        """실패 알림 처리"""
        if not execution_data.get("success"):
            await self.send_email_alert(execution_data)
            # await self.send_sms_alert(execution_data)
        