import { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Space,
  Card,
  Row,
  Col,
  Tag,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  DownloadOutlined,
  DeleteOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { componentsAPI } from '../services/api';

export default function Components() {
  const [components, setComponents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchComponents();
  }, [pagination.current, pagination.pageSize]);

  const fetchComponents = async () => {
    setLoading(true);
    try {
      const skip = (pagination.current - 1) * pagination.pageSize;
      const response = await componentsAPI.list(skip, pagination.pageSize);
      setComponents(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      message.error('获取组件列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (values) => {
    try {
      await componentsAPI.create(values);
      message.success('组件注册成功');
      setIsModalVisible(false);
      form.resetFields();
      fetchComponents();
    } catch (error) {
      const errorMsg = error.response?.data?.detail || '注册失败';
      message.error(errorMsg);
    }
  };

  const handleInstall = async (componentId) => {
    const hide = message.loading('正在安装...', 0);
    try {
      await componentsAPI.install(componentId, false);
      message.success('安装成功');
      fetchComponents();
    } catch (error) {
      message.error('安装失败');
    } finally {
      hide();
    }
  };

  const handleUninstall = (componentId) => {
    Modal.confirm({
      title: '卸载组件',
      content: '确定要卸载此组件吗？',
      okText: '确定',
      cancelText: '取消',
      onOk: async () => {
        try {
          await componentsAPI.uninstall(componentId);
          message.success('卸载成功');
          fetchComponents();
        } catch (error) {
          message.error('卸载失败');
        }
      },
    });
  };

  const handleCheckUpdate = async (componentId) => {
    try {
      const response = await componentsAPI.checkUpdate(componentId);
      const { current_version, latest_version, update_available } = response.data;
      
      if (update_available) {
        Modal.confirm({
          title: '发现新版本',
          content: `当前版本: ${current_version}\n最新版本: ${latest_version}\n\n是否立即升级？`,
          okText: '升级',
          cancelText: '取消',
          onOk: () => handleUpgrade(componentId),
        });
      } else {
        message.info('已是最新版本');
      }
    } catch (error) {
      message.error('检查更新失败');
    }
  };

  const handleUpgrade = async (componentId) => {
    const hide = message.loading('正在升级...', 0);
    try {
      await componentsAPI.upgrade(componentId);
      message.success('升级成功');
      fetchComponents();
    } catch (error) {
      message.error('升级失败');
    } finally {
      hide();
    }
  };

  const handleDelete = (componentId) => {
    Modal.confirm({
      title: '删除组件',
      content: '确定要删除此组件吗？此操作不可撤销。',
      okText: '确定',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await componentsAPI.delete(componentId);
          message.success('删除成功');
          fetchComponents();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const columns = [
    {
      title: '组件名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type) => {
        const colors = { proxy: 'blue', tool: 'green' };
        return <Tag color={colors[type]}>{type === 'proxy' ? '代理' : '工具'}</Tag>;
      },
    },
    {
      title: '当前版本',
      dataIndex: 'version',
      key: 'version',
      width: 120,
    },
    {
      title: '最新版本',
      dataIndex: 'latest_version',
      key: 'latest_version',
      width: 120,
      render: (version) => version || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => {
        const statusMap = {
          'installed': { color: 'green', text: '已安装', icon: <CheckCircleOutlined /> },
          'not-installed': { color: 'default', text: '未安装', icon: <CloseCircleOutlined /> },
          'installing': { color: 'blue', text: '安装中', icon: <SyncOutlined spin /> },
          'error': { color: 'red', text: '错误', icon: <CloseCircleOutlined /> },
        };
        const config = statusMap[status] || statusMap['not-installed'];
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 250,
      render: (_, record) => (
        <Space wrap>
          {record.status === 'not-installed' && (
            <Tooltip title="安装">
              <Button
                size="small"
                type="primary"
                icon={<DownloadOutlined />}
                onClick={() => handleInstall(record.id)}
              >
                安装
              </Button>
            </Tooltip>
          )}
          
          {record.status === 'installed' && (
            <>
              <Tooltip title="检查更新">
                <Button
                  size="small"
                  icon={<SyncOutlined />}
                  onClick={() => handleCheckUpdate(record.id)}
                />
              </Tooltip>
              
              <Tooltip title="卸载">
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleUninstall(record.id)}
                />
              </Tooltip>
            </>
          )}
          
          <Tooltip title="删除记录">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
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
            <h2>组件管理</h2>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsModalVisible(true)}
            >
              注册组件
            </Button>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={components}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个组件`,
            onChange: (page, pageSize) => {
              setPagination({ current: page, pageSize });
            },
          }}
        />
      </Card>

      <Modal
        title="注册组件"
        open={isModalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
        >
          <Form.Item
            name="name"
            label="组件名称"
            rules={[{ required: true, message: '请输入组件名称' }]}
          >
            <Input placeholder="例如：sing-box" />
          </Form.Item>

          <Form.Item
            name="type"
            label="组件类型"
            rules={[{ required: true, message: '请选择组件类型' }]}
          >
            <Select
              placeholder="选择类型"
              options={[
                { label: '代理组件', value: 'proxy' },
                { label: '工具组件', value: 'tool' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="version"
            label="版本号"
            rules={[{ required: true, message: '请输入版本号' }]}
          >
            <Input placeholder="例如：1.0.0" />
          </Form.Item>

          <Form.Item
            name="install_method"
            label="安装方式"
            rules={[{ required: true, message: '请选择安装方式' }]}
          >
            <Select
              placeholder="选择安装方式"
              options={[
                { label: '二进制文件', value: 'binary' },
                { label: 'Docker', value: 'docker' },
                { label: '脚本安装', value: 'script' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="install_url"
            label="安装 URL（可选）"
          >
            <Input placeholder="下载链接或仓库地址" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
