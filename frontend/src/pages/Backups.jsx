import { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Checkbox,
  Input,
  message,
  Space,
  Card,
  Row,
  Col,
  Tooltip,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  DownloadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { backupsAPI } from '../services/api';

export default function Backups() {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const [isCreateModalVisible, setIsCreateModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchBackups();
  }, []);

  const fetchBackups = async () => {
    setLoading(true);
    try {
      const response = await backupsAPI.list();
      setBackups(response.data.items);
    } catch (error) {
      message.error('获取备份列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (values) => {
    const hide = message.loading('正在创建备份...', 0);
    try {
      await backupsAPI.create(
        values.include_data,
        values.include_config,
        values.description
      );
      message.success('备份创建成功');
      setIsCreateModalVisible(false);
      form.resetFields();
      fetchBackups();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || '创建失败';
      message.error(errorMsg);
    } finally {
      hide();
    }
  };

  const handleRestore = (filename) => {
    Modal.confirm({
      title: '恢复备份',
      content: '确定要恢复此备份吗？这将覆盖当前数据。',
      okText: '确定',
      cancelText: '取消',
      okType: 'warning',
      onOk: async () => {
        const hide = message.loading('正在恢复备份...', 0);
        try {
          await backupsAPI.restore(filename, false);
          message.success('备份恢复成功');
          fetchBackups();
        } catch (error) {
          message.error('恢复失败');
        } finally {
          hide();
        }
      },
    });
  };

  const handleDownload = async (filename) => {
    try {
      const response = await backupsAPI.download(filename);
      
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      message.success('下载成功');
    } catch (error) {
      message.error('下载失败');
    }
  };

  const handleDelete = (filename) => {
    Modal.confirm({
      title: '删除备份',
      content: '确定要删除此备份吗？此操作不可撤销。',
      okText: '确定',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await backupsAPI.delete(filename);
          message.success('删除成功');
          fetchBackups();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const handleCleanup = () => {
    Modal.confirm({
      title: '清理旧备份',
      content: '确定要清理 30 天前的备份吗？',
      okText: '确定',
      cancelText: '取消',
      okType: 'warning',
      onOk: async () => {
        try {
          const response = await backupsAPI.cleanup(30);
          message.success(response.data.message);
          fetchBackups();
        } catch (error) {
          message.error('清理失败');
        }
      },
    });
  };

  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      width: 300,
    },
    {
      title: '大小',
      dataIndex: 'size_mb',
      key: 'size_mb',
      width: 120,
      render: (size) => `${size.toFixed(2)} MB`,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 200,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (desc) => desc || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space wrap>
          <Tooltip title="恢复">
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRestore(record.filename)}
            >
              恢复
            </Button>
          </Tooltip>
          
          <Tooltip title="下载">
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record.filename)}
            />
          </Tooltip>
          
          <Tooltip title="删除">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.filename)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <h2>备份管理</h2>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ClearOutlined />}
                onClick={handleCleanup}
              >
                清理旧备份
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setIsCreateModalVisible(true)}
              >
                创建备份
              </Button>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={backups}
          rowKey="filename"
          loading={loading}
          pagination={false}
        />
      </Card>

      <Modal
        title="创建备份"
        open={isCreateModalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsCreateModalVisible(false);
          form.resetFields();
        }}
        width={500}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{
            include_data: true,
            include_config: true,
          }}
        >
          <Form.Item
            name="include_data"
            valuePropName="checked"
          >
            <Checkbox>包含数据库数据</Checkbox>
          </Form.Item>

          <Form.Item
            name="include_config"
            valuePropName="checked"
          >
            <Checkbox>包含配置文件</Checkbox>
          </Form.Item>

          <Form.Item
            name="description"
            label="备份描述（可选）"
          >
            <Input.TextArea
              rows={3}
              placeholder="备份的说明信息"
              maxLength={255}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
