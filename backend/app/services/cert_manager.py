"""
证书管理服务 - 支持 DNS API 自动签发和续期
文件：backend/app/services/cert_manager.py
"""
import os
import subprocess
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.domain import Domain
from app.config import settings

logger = logging.getLogger(__name__)


class CertManager:
    """证书管理类"""
    
    # acme.sh 路径
    ACME_HOME = os.path.expanduser("~/.acme.sh")
    ACME_SH = os.path.join(ACME_HOME, "acme.sh")
    
    # 证书存储路径
    CERTS_DIR = getattr(settings, 'CERTS_DIR', '/opt/atlas/certs')
    
    # 支持的 DNS 提供商
    SUPPORTED_PROVIDERS = {
        'cloudflare': {
            'name': 'Cloudflare',
            'dns_type': 'dns_cf',
            'required_keys': ['CF_Key', 'CF_Email'],
            'key_names': {
                'CF_Key': 'API Key',
                'CF_Email': 'Email',
            }
        },
        'aliyun': {
            'name': '阿里云',
            'dns_type': 'dns_ali',
            'required_keys': ['Ali_Key', 'Ali_Secret'],
            'key_names': {
                'Ali_Key': 'Access Key ID',
                'Ali_Secret': 'Access Key Secret',
            }
        },
        'dnspod': {
            'name': 'DNSPod',
            'dns_type': 'dns_dp',
            'required_keys': ['DP_Id', 'DP_Key'],
            'key_names': {
                'DP_Id': 'API ID',
                'DP_Key': 'API Key',
            }
        },
        'godaddy': {
            'name': 'GoDaddy',
            'dns_type': 'dns_gd',
            'required_keys': ['GD_Key', 'GD_Secret'],
            'key_names': {
                'GD_Key': 'API Key',
                'GD_Secret': 'API Secret',
            }
        },
        'standalone': {
            'name': '独立模式（需要 80 端口）',
            'dns_type': None,
            'required_keys': [],
            'key_names': {}
        }
    }
    
    @staticmethod
    def check_acme_installed() -> bool:
        """检查 acme.sh 是否已安装"""
        return os.path.exists(CertManager.ACME_SH)
    
    @staticmethod
    def install_acme() -> Dict:
        """安装 acme.sh"""
        try:
            logger.info("📦 开始安装 acme.sh...")
            
            # 下载安装脚本
            install_cmd = [
                'curl', 'https://get.acme.sh',
                '-o', '/tmp/acme_install.sh'
            ]
            subprocess.run(install_cmd, check=True, capture_output=True)
            
            # 执行安装
            subprocess.run(
                ['sh', '/tmp/acme_install.sh'],
                check=True,
                capture_output=True,
                text=True,
            )
            
            logger.info("✅ acme.sh 安装成功")
            return {
                'success': True,
                'message': 'acme.sh 安装成功',
                'version': CertManager.get_acme_version(),
            }
        
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            logger.error(f"❌ acme.sh 安装失败: {error_msg}")
            return {
                'success': False,
                'error': f'安装失败: {error_msg}',
            }
        except Exception as e:
            logger.error(f"❌ acme.sh 安装失败: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def get_acme_version() -> Optional[str]:
        """获取 acme.sh 版本"""
        try:
            result = subprocess.run(
                [CertManager.ACME_SH, '--version'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # 输出格式: v3.0.7
                return result.stdout.strip()
            return None
        except Exception as e:
            logger.error(f"获取 acme.sh 版本失败: {e}")
            return None
    
    @staticmethod
    def issue_cert_standalone(
        domain: str,
        email: str,
    ) -> Dict:
        """使用 standalone 模式签发证书"""
        try:
            cert_dir = Path(CertManager.CERTS_DIR) / domain
            cert_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"📝 开始签发证书（standalone）: {domain}")
            
            # 停止占用 80 端口的服务（如 Nginx）
            CertManager._stop_web_server()
            
            try:
                # 执行签发
                cmd = [
                    CertManager.ACME_SH,
                    '--issue',
                    '-d', domain,
                    '--standalone',
                    '--httpport', '80',
                    '-m', email,
                    '--cert-file', str(cert_dir / 'cert.pem'),
                    '--key-file', str(cert_dir / 'privkey.pem'),
                    '--fullchain-file', str(cert_dir / 'fullchain.pem'),
                    '--force',
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                
                if result.returncode == 0:
                    # 设置证书文件权限
                    CertManager._set_cert_permissions(cert_dir)
                    
                    logger.info(f"✅ 证书签发成功: {domain}")
                    return {
                        'success': True,
                        'message': '证书签发成功',
                        'cert_path': str(cert_dir),
                        'valid_from': datetime.now(),
                        'valid_to': datetime.now() + timedelta(days=90),
                    }
                else:
                    error_msg = result.stderr or result.stdout
                    logger.error(f"❌ 证书签发失败: {error_msg}")
                    return {
                        'success': False,
                        'error': f'签发失败: {error_msg}',
                    }
            
            finally:
                # 重启 Web 服务器
                CertManager._start_web_server()
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': '签发超时（120秒）',
            }
        except Exception as e:
            logger.error(f"❌ 证书签发失败: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def issue_cert_dns(
        domain: str,
        email: str,
        provider: str,
        api_credentials: Dict[str, str],
    ) -> Dict:
        """使用 DNS API 签发证书"""
        try:
            # 验证提供商
            if provider not in CertManager.SUPPORTED_PROVIDERS:
                return {
                    'success': False,
                    'error': f'不支持的提供商: {provider}',
                }
            
            provider_config = CertManager.SUPPORTED_PROVIDERS[provider]
            dns_type = provider_config['dns_type']
            
            if not dns_type:
                return {
                    'success': False,
                    'error': '该提供商不支持 DNS API',
                }
            
            # 验证必需的凭证
            required_keys = provider_config['required_keys']
            for key in required_keys:
                if key not in api_credentials:
                    return {
                        'success': False,
                        'error': f'缺少必需的凭证: {provider_config["key_names"][key]}',
                    }
            
            cert_dir = Path(CertManager.CERTS_DIR) / domain
            cert_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"📝 开始签发证书（DNS API - {provider}）: {domain}")
            
            # 准备环境变量
            env = os.environ.copy()
            for key, value in api_credentials.items():
                env[key] = value
            
            # 执行签发
            cmd = [
                CertManager.ACME_SH,
                '--issue',
                '-d', domain,
                '--dns', dns_type,
                '-m', email,
                '--cert-file', str(cert_dir / 'cert.pem'),
                '--key-file', str(cert_dir / 'privkey.pem'),
                '--fullchain-file', str(cert_dir / 'fullchain.pem'),
                '--force',
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,  # DNS 验证可能需要更长时间
            )
            
            if result.returncode == 0:
                # 设置证书文件权限
                CertManager._set_cert_permissions(cert_dir)
                
                logger.info(f"✅ 证书签发成功（DNS API）: {domain}")
                return {
                    'success': True,
                    'message': '证书签发成功',
                    'cert_path': str(cert_dir),
                    'valid_from': datetime.now(),
                    'valid_to': datetime.now() + timedelta(days=90),
                }
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"❌ 证书签发失败: {error_msg}")
                return {
                    'success': False,
                    'error': f'签发失败: {error_msg}',
                }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': '签发超时（300秒）',
            }
        except Exception as e:
            logger.error(f"❌ 证书签发失败: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def renew_cert(
        domain: str,
        provider: str = 'standalone',
        api_credentials: Dict[str, str] = None,
    ) -> Dict:
        """续期证书"""
        try:
            logger.info(f"🔄 开始续期证书: {domain}")
            
            # 准备环境变量
            env = os.environ.copy()
            if api_credentials:
                for key, value in api_credentials.items():
                    env[key] = value
            
            cert_dir = Path(CertManager.CERTS_DIR) / domain
            
            # 执行续期
            cmd = [
                CertManager.ACME_SH,
                '--renew',
                '-d', domain,
                '--cert-file', str(cert_dir / 'cert.pem'),
                '--key-file', str(cert_dir / 'privkey.pem'),
                '--fullchain-file', str(cert_dir / 'fullchain.pem'),
                '--force',
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            if result.returncode == 0:
                logger.info(f"✅ 证书续期成功: {domain}")
                return {
                    'success': True,
                    'message': '证书续期成功',
                    'renewed_at': datetime.now(),
                    'valid_to': datetime.now() + timedelta(days=90),
                }
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"❌ 证书续期失败: {error_msg}")
                return {
                    'success': False,
                    'error': f'续期失败: {error_msg}',
                }
        
        except Exception as e:
            logger.error(f"❌ 证书续期失败: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def get_cert_info(domain: str) -> Optional[Dict]:
        """获取证书信息"""
        try:
            cert_path = Path(CertManager.CERTS_DIR) / domain / 'fullchain.pem'
            
            if not cert_path.exists():
                return None
            
            # 使用 openssl 读取证书信息
            cmd = [
                'openssl', 'x509',
                '-in', str(cert_path),
                '-noout',
                '-dates',
                '-subject',
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                
                info = {
                    'domain': domain,
                    'cert_path': str(cert_path),
                    'exists': True,
                }
                
                for line in lines:
                    if line.startswith('notBefore='):
                        info['valid_from'] = line.replace('notBefore=', '').strip()
                    elif line.startswith('notAfter='):
                        info['valid_to'] = line.replace('notAfter=', '').strip()
                    elif line.startswith('subject='):
                        info['subject'] = line.replace('subject=', '').strip()
                
                return info
            
            return None
        
        except Exception as e:
            logger.error(f"获取证书信息失败: {e}")
            return None
    
    @staticmethod
    def check_expiring_certs(db: Session, days: int = 30) -> List[Domain]:
        """检查即将过期的证书"""
        try:
            now = datetime.now()
            expiry_date = now + timedelta(days=days)
            
            domains = db.query(Domain).filter(
                Domain.cert_valid_to <= expiry_date,
                Domain.cert_valid_to > now,
                Domain.auto_renew == True,
            ).all()
            
            return domains
        
        except Exception as e:
            logger.error(f"检查过期证书失败: {e}")
            return []
    
    @staticmethod
    def _stop_web_server():
        """停止 Web 服务器"""
        try:
            subprocess.run(['systemctl', 'stop', 'nginx'], capture_output=True)
            logger.info("⏹️  Nginx 已停止")
        except Exception as e:
            logger.warning(f"停止 Nginx 失败: {e}")
    
    @staticmethod
    def _start_web_server():
        """启动 Web 服务器"""
        try:
            subprocess.run(['systemctl', 'start', 'nginx'], capture_output=True)
            logger.info("▶️  Nginx 已启动")
        except Exception as e:
            logger.warning(f"启动 Nginx 失败: {e}")
    
    @staticmethod
    def _set_cert_permissions(cert_dir: Path):
        """设置证书文件权限"""
        try:
            for cert_file in cert_dir.glob('*.pem'):
                os.chmod(cert_file, 0o600)
            logger.info(f"🔒 证书权限已设置: {cert_dir}")
        except Exception as e:
            logger.warning(f"设置权限失败: {e}")
    
    @staticmethod
    def get_supported_providers() -> Dict:
        """获取支持的 DNS 提供商列表"""
        return CertManager.SUPPORTED_PROVIDERS
