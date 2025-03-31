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
        그룹명: {execution_data['group_name']}
        프로세스명명: {execution_data['process_name']}
        시작 시간: {execution_data['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
        종료 시간: {execution_data['end_time'].strftime('%Y-%m-%d %H:%M:%S')}
        실행 시간: {execution_data['duration_seconds']:.2f}초
        
        오류 유형: {execution_data['error_type']}
        오류 메시지: {execution_data['error_message']}
        """
        logger.info(f"이메일 내용: {body}")

        html_body = f"""
    <html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <title>ETL 프로세스 오류 알림</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
        <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
            <!-- 헤더 -->
            <div style="background-color: #1e88e5; color: white; padding: 15px; border-radius: 5px 5px 0 0; text-align: center;">
                <h2 style="margin: 0;">ETL 프로세스 오류 알림</h2>
            </div>
            
            <!-- 컨텐츠 영역 -->
            <div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 5px 5px; background-color: #f9f9f9;">
                <!-- 메트릭 블록 -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 20px;">
                    <tr>
                        <!-- 실행 시간 -->
                        <td width="33%" style="text-align: center; padding: 15px;">
                            <div style="background-color: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="font-size: 14px; color: #777;">실행 시간</div>
                                <div style="font-size: 24px; font-weight: bold; margin: 10px 0; color: #1e88e5;">{execution_data['duration_seconds']:.2f}초</div>
                            </div>
                        </td>
                        
                        <!-- 상태 -->
                        <td width="33%" style="text-align: center; padding: 15px;">
                            <div style="background-color: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="font-size: 14px; color: #777;">상태</div>
                                <div style="font-size: 24px; font-weight: bold; margin: 10px 0; color: #f44336;">실패</div>
                            </div>
                        </td>
                        
                        <!-- 플랫폼 -->
                        <td width="33%" style="text-align: center; padding: 15px;">
                            <div style="background-color: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="font-size: 14px; color: #777;">플랫폼</div>
                                <div style="font-size: 24px; font-weight: bold; margin: 10px 0;">
                                    <span style="background-color: #1976d2; color: white; padding: 3px 8px; border-radius: 3px;">{execution_data['platform_type']}</span>
                                </div>
                            </div>
                        </td>
                    </tr>
                </table>
                
                <!-- 프로세스 정보 테이블 -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; margin-bottom: 20px; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <th colspan="6" style="background-color: #2196f3; color: white; text-align: left; padding: 12px;">프로세스 실행 정보</th>
                    </tr>
                    <tr>
                        <td width="15%" style="padding: 12px; border: 1px solid #e0e0e0;"><strong>서버</strong></td>
                        <td width="25%" style="padding: 12px; border: 1px solid #e0e0e0;">{execution_data['host_name']}</td>
                        <td width="15%" style="padding: 12px; border: 1px solid #e0e0e0;"><strong>그룹명</strong></td>
                        <td width="20%" style="padding: 12px; border: 1px solid #e0e0e0;">{execution_data['group_name']}</td>
                        <td width="10%" style="padding: 12px; border: 1px solid #e0e0e0;"><strong>프로세스</strong></td>
                        <td width="15%" style="padding: 12px; border: 1px solid #e0e0e0;">{execution_data['process_name']}</td>
                    </tr>
                    <tr style="background-color: #f2f9ff;">
                        <td style="padding: 12px; border: 1px solid #e0e0e0;"><strong>시작 시간</strong></td>
                        <td style="padding: 12px; border: 1px solid #e0e0e0;">{execution_data['start_time'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                        <td style="padding: 12px; border: 1px solid #e0e0e0;"><strong>종료 시간</strong></td>
                        <td style="padding: 12px; border: 1px solid #e0e0e0;">{execution_data['end_time'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                        <td style="padding: 12px; border: 1px solid #e0e0e0;"><strong>실행 시간</strong></td>
                        <td style="padding: 12px; border: 1px solid #e0e0e0;">{execution_data['duration_seconds']:.2f}초</td>
                    </tr>
                </table>
                
                <!-- 오류 정보 -->
                <div style="background-color: #ffebee; border-left: 5px solid #f44336; padding: 15px; margin-top: 20px;">
                    <div style="font-weight: bold; color: #d32f2f; font-size: 18px; margin-bottom: 10px;">❌ 오류 발생</div>
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <tr>
                            <td width="20%" style="padding: 12px; border: 1px solid #e0e0e0;"><strong>오류 유형</strong></td>
                            <td style="padding: 12px; border: 1px solid #e0e0e0;">
                                <span style="background-color: #f44336; color: white; padding: 5px 10px; border-radius: 3px; display: inline-block;">{execution_data['error_type']}</span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid #e0e0e0;"><strong>오류 메시지</strong></td>
                            <td style="padding: 12px; border: 1px solid #e0e0e0;">
                                <div style="font-family: monospace; white-space: pre-wrap; padding: 12px; background-color: #fff; border: 1px solid #ffcdd2; border-radius: 3px; overflow-x: auto;">{execution_data['error_message']}</div>
                            </td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <!-- 푸터 -->
            <div style="margin-top: 20px; font-size: 12px; color: #777; text-align: center; padding-top: 15px; border-top: 1px solid #ddd;">
                이 메일은 자동으로 발송되었습니다. | 시스템: ETL 모니터링 시스템 | 시간: {execution_data['end_time'].strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
    </body>
    </html>
    """
        # msg.set_content(body)
        msg.add_alternative(html_body, subtype="html")
        
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
    
    