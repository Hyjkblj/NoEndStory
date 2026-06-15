/**
 * 登录页面
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, App as AntdApp, Divider } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useAuth } from '@/stores/authStore';
import { ROUTES } from '@/config/routes';

const { Title, Text } = Typography;

interface LoginFormValues {
  email: string;
  password: string;
}

function Login() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const { login, isLoading, error, clearError } = useAuth();
  const [form] = Form.useForm<LoginFormValues>();

  const handleSubmit = async (values: LoginFormValues) => {
    try {
      await login(values.email, values.password);
      message.success('登录成功！');
      navigate(ROUTES.HOME);
    } catch (error) {
      // 错误已经在authStore中处理
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '20px',
      }}
    >
      <div
        style={{
          background: 'white',
          borderRadius: '12px',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
          padding: '40px',
          width: '100%',
          maxWidth: '400px',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <Title level={2} style={{ marginBottom: '8px', color: '#333' }}>
            欢迎回来
          </Title>
          <Text type="secondary">登录您的账户以继续游戏</Text>
        </div>

        {error && (
          <div
            style={{
              background: '#fff2f0',
              border: '1px solid #ffccc7',
              borderRadius: '6px',
              padding: '8px 12px',
              marginBottom: '20px',
              color: '#ff4d4f',
            }}
          >
            {error}
            <Button
              type="link"
              size="small"
              onClick={clearError}
              style={{ float: 'right', padding: 0 }}
            >
              关闭
            </Button>
          </div>
        )}

        <Form
          form={form}
          onFinish={handleSubmit}
          layout="vertical"
          requiredMark={false}
        >
          <Form.Item
            name="email"
            rules={[
              { required: true, message: '请输入邮箱地址' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="邮箱地址"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码至少8个字符' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              size="large"
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: '16px' }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={isLoading}
              block
              size="large"
              style={{
                height: '48px',
                fontSize: '16px',
                fontWeight: 'bold',
              }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <Link to="/forgot-password" style={{ color: '#667eea' }}>
            忘记密码？
          </Link>
        </div>

        <Divider style={{ margin: '20px 0' }}>或者</Divider>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">还没有账户？</Text>
          <Link
            to="/register"
            style={{
              color: '#667eea',
              fontWeight: 'bold',
              marginLeft: '8px',
            }}
          >
            立即注册
          </Link>
        </div>

        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <Button
            type="default"
            onClick={() => navigate(ROUTES.HOME)}
            style={{ width: '100%' }}
          >
            返回首页
          </Button>
        </div>
      </div>
    </div>
  );
}

export default Login;