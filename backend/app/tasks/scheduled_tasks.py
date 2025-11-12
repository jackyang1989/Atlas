"""
定时任务管理 - 包括自动备份、证书续期检查等
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 全局调度器
scheduler: BackgroundScheduler = None


def init_scheduler():
    """初始化定时任务调度器"""
    global scheduler
    
    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("✅ 定时任务调度器已启动")


def register_scheduled_tasks(db_session_factory):
    """注册所有定时任务"""
    
    init_scheduler()
    
    # ==================== 1. 自动备份任务 ====================
    def auto_backup_task():
        """每天凌晨 2 点执行自动备份"""
        try:
            from app.services.backup_service import get_backup_service
            from app.database import SessionLocal
            
            db = SessionLocal()
            try:
                backup_service = get_backup_service()
                result = backup_service.create_backup(
                    db,
                    include_data=True,
                    include_config=True,
                    description=f"自动备份 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                if result.get('success'):
                    logger.info(f"✅ 自动备份成功: {result['filename']}")
                    
                    # 清理 30 天前的备份
                    cleanup_result = backup_service.cleanup_old_backups(days=30)
                    if cleanup_result.get('success'):
                        logger.info(f"✅ 清理过期备份: 删除 {cleanup_result['deleted_count']} 个")
                else:
                    logger.error(f"❌ 自动备份失败: {result.get('error')}")
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"❌ 自动备份任务出错: {e}")
    
    # ==================== 2. 证书续期检查 ====================
    def auto_renew_certificates_task():
        """每天凌晨 3 点检查证书续期"""
        try:
            from app.database import SessionLocal
            from app.models.domain import Domain
            from datetime import timedelta
            
            db = SessionLocal()
            try:
                # 查找需要续期的域名
                now = datetime.now()
                domains_to_renew = db.query(Domain).filter(
                    Domain.cert_valid_to <= now + timedelta(days=30),
                    Domain.cert_valid_to > now,
                    Domain.auto_renew == True,
                ).all()
                
                if domains_to_renew:
                    logger.info(f"⚠️ 发现 {len(domains_to_renew)} 个域名需要续期")
                    
                    # TODO: 实现证书续期逻辑
                    # for domain in domains_to_renew:
                    #     logger.info(f"续期证书: {domain.domain}")
                else:
                    logger.info("✅ 所有证书状态正常，暂无需续期")
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"❌ 证书续期检查任务出错: {e}")
    
    # ==================== 3. 用户过期检查 ====================
    def check_expired_users_task():
        """每小时检查过期用户并禁用"""
        try:
            from app.database import SessionLocal
            from app.models.user import User
            
            db = SessionLocal()
            try:
                now = datetime.now()
                
                # 查找过期用户
                expired_users = db.query(User).filter(
                    User.expiry_date <= now,
                    User.status == "active"
                ).all()
                
                if expired_users:
                    for user in expired_users:
                        user.status = "expired"
                        logger.info(f"⚠️ 用户已过期: {user.username}")
                    
                    db.commit()
                    logger.info(f"✅ 已禁用 {len(expired_users)} 个过期用户")
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"❌ 用户过期检查任务出错: {e}")
    
    # ==================== 4. 系统资源告警检查 ====================
    def check_system_resources_task():
        """每 5 分钟检查系统资源使用情况"""
        try:
            import psutil
            from app.services.alert_manager import alert_manager
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            thresholds = {
                'cpu': 90,      # CPU 使用率 > 90%
                'memory': 90,   # 内存 > 90%
                'disk': 85,     # 磁盘 > 85%
            }
            
            issues = []
            
            if cpu_percent > thresholds['cpu']:
                issues.append(f"CPU 使用率过高: {cpu_percent}%")
            
            if memory.percent > thresholds['memory']:
                issues.append(f"内存使用率过高: {memory.percent}%")
            
            if disk.percent > thresholds['disk']:
                issues.append(f"磁盘使用率过高: {disk.percent}%")
            
            if issues:
                issue_text = "\n".join(issues)
                logger.warning(f"⚠️ 系统资源告警:\n{issue_text}")
                
                # TODO: 发送告警邮件给管理员
                # admin_emails = get_admin_emails()
                # alert_manager.send_system_resource_alert(...)
        
        except Exception as e:
            logger.error(f"❌ 系统资源检查任务出错: {e}")
    
    # ==================== 注册任务 ====================
    
    # 每天凌晨 2 点执行自动备份
    scheduler.add_job(
        auto_backup_task,
        CronTrigger(hour=2, minute=0),
        id='auto_backup',
        name='自动备份',
        replace_existing=True
    )
    logger.info("📅 已注册任务: 自动备份 (每天 02:00)")
    
    # 每天凌晨 3 点检查证书续期
    scheduler.add_job(
        auto_renew_certificates_task,
        CronTrigger(hour=3, minute=0),
        id='check_certs',
        name='证书续期检查',
        replace_existing=True
    )
    logger.info("📅 已注册任务: 证书续期检查 (每天 03:00)")
    
    # 每小时检查用户过期
    scheduler.add_job(
        check_expired_users_task,
        CronTrigger(minute=0),
        id='check_users',
        name='用户过期检查',
        replace_existing=True
    )
    logger.info("📅 已注册任务: 用户过期检查 (每小时)")
    
    # 每 5 分钟检查系统资源
    scheduler.add_job(
        check_system_resources_task,
        CronTrigger(minute='*/5'),
        id='check_resources',
        name='系统资源检查',
        replace_existing=True
    )
    logger.info("📅 已注册任务: 系统资源检查 (每 5 分钟)")


def start_scheduler():
    """启动调度器"""
    global scheduler
    if scheduler and not scheduler.running:
        scheduler.start()
        logger.info("✅ 定时任务调度器已启动")


def stop_scheduler():
    """停止调度器"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("👋 定时任务调度器已停止")


def get_scheduler_status():
    """获取调度器状态"""
    global scheduler
    if scheduler is None:
        return {"status": "not_initialized"}
    
    return {
        "status": "running" if scheduler.running else "stopped",
        "jobs": len(scheduler.get_jobs()),
        "jobs_detail": [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time),
            }
            for job in scheduler.get_jobs()
        ]
    }
