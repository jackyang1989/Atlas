import { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
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
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CopyOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { servicesAPI } from '../services/api';
import '../styles/Services.css';

export default function Services() {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchServices();
  }, [pagination]);

  const fetchServices = async () => {
    setLoading(true);
    try {
      const skip = (pagination.current - 1) * pagination.pageSize;
      const response = await servicesAPI.list(skip, pagination.pageSize);
      setServices(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      message.error('获取服务列表失败');
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrUpdate = async (values) => {
    try {
      if (editingId) {
        await servicesAPI.update(editingId, values);
        message.success('服务已更新');
      } else {
        await servicesAPI.create(values);
        message.success('服务创建成功');
      }
      setIsModalVisible(false);
      form.resetFields();
      setEditingId(null);
      fetchServices();
    } catch (error) {
      const errorMsg =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        '操作失败';
      message.error(errorMsg);
    }
  };

  const handleToggleService = async (serviceId, currentStatus) => {
    try {
      await servicesAPI.toggle(serviceId);
      const newStatus = currentStatus === 'running' ? '已停止' : '已启动';
      message.success(`服务${newStatus}`);
      fetchServices();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDeleteService = (serviceId) => {
    Modal.confirm({
      title: '删除服务',
      content: '确定要删除此服务吗？此操作不可撤销。',
      okText: '确定',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          await servicesAPI.delete(serviceId);
          message.success('服务已删除');
          fetchServices();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const handleShowModal = (record = null) => {
    if (record) {
      setEditingId(record.id);
      form.setFieldsValue({
        name: record.name,
        protocol: record.protocol,
        port: record.port,
        cert_domain: record.cert_domain,
        tags: record.tags,
      });
    } else {
      setEditingId(null);
      form.resetFields();
    }
    setIsModalVisible(true);
  };

  const columns = [
    {
      title: '服务名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '协议',
      dataIndex: 'protocol',
      key: 'protocol',
      width: 100,
      render: (protocol) => {
        const colors = {
          vless: 'blue',
          hysteria2: 'green',
          tuic: 'orange',
          trojan: 'red',
        };
        return <Tag color={colors[protocol] || 'default'}>{protocol.toUpperCase()}</Tag>;
      },
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port',
      width: 80,
      sorter: (a, b) => a.port - b.port,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status) => {
        const color = status === 'running' ? 'green' : 'red';
        const text = status === 'running' ? '运行中' : '已停止';
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '证书域名',
      dataIndex: 'cert_domain',
      key: 'cert_domain',
      width: 150,
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      fixed: 'right',
      render: (_, record) => (
        <Space wrap>
          <Tooltip title={record.status === 'running' ? '停止' : '启动'}>
            <Button
              size="small"
              icon={
                record.status === 'running' ? (
                  <PauseCircleOutlined />
                ) : (
                  <PlayCircleOutlined />
                )
              }
              onClick={() => handleToggleService(record.id, record.status)}
            />
          </Tooltip>
          
          <Tooltip title="编辑">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleShowModal(record)}
            />
          </Tooltip>
          
          <Tooltip title="删除">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteService(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="services-container">
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <h2>VPN 服务管理</h2>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchServices}
                loading={loading}
              >
                刷新
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => handleShowModal()}
              >
                创建服务
              </Button>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={services}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个服务`,
            onChange: (page, pageSize) => {
              setPagination({ current: page, pageSize });
            },
          }}
        />
      </Card>

      <Modal
        title={editingId ? '编辑服务' : '创建服务'}
        open={isModalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
          setEditingId(null);
        }}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateOrUpdate}
        >
          <Form.Item
            name="name"
            label="服务名称"
            rules={[
              { required: true, message: '请输入服务名称' },
              { min: 1, max: 100, message: '名称长度 1-100 字符' },
            ]}
          >
            <Input placeholder="例如：VLESS_HK_01" />
          </Form.Item>

          <Form.Item
            name="protocol"
            label="协议类型"
            rules={[{ required: true, message: '请选择协议' }]}
          >
            <Select
              placeholder="选择协议"
              options={[
                { label: 'VLESS', value: 'vless' },
                { label: 'Hysteria2', value: 'hysteria2' },
                { label: 'TUIC', value: 'tuic' },
                { label: 'Trojan', value: 'trojan' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="port"
            label="监听端口"
            rules={[
              { required: true, message: '请输入端口' },
              { type: 'number', min: 1, max: 65535, message: '端口范围 1-65535' },
            ]}
          >
            <InputNumber
              min={1}
              max={65535}
              placeholder="1-65535"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            name="cert_domain"
            label="证书域名（VLESS 必需）"
            tooltip="VLESS 协议需要配置 TLS 证书域名"
          >
            <Input placeholder="例如：example.com" />
          </Form.Item>

          <Form.Item
            name="tags"
            label="地域标签"
            tooltip="可选，用于标记服务所在地区，JSON 格式"
          >
            <Input placeholder='["CN", "HK"]' />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
