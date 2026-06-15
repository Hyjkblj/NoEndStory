/**
 * 注册页面
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, App as AntdApp, Divider, Checkbox } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useAuth } from '@/stores/authStore';
import { ROUTES } from '@/config/routes';

const { Title, Text } = Typography;

interface RegisterFormValues {
  email: string;
  username: string;
  password: string;
  confirmPassword: string;
  agreeTerms: boolean;
}

function Register() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const { register, isLoading, error, clearError } = useAuth();
  const [form] = Form.useForm<RegisterFormValues>();

  const handleSubmit = async (values: RegisterFormValues) => {
    try {
      await register(values.email, values.username, values.password);
      message.success('注册成功！');
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
            创建账户
          </Title>
          <Text type="secondary">注册以保存游戏进度和角色</Text>
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
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少3个字符' },
              { max: 50, message: '用户名最多50个字符' },
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码至少8个字符' },
              { max: 128, message: '密码最多128个字符' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="确认密码"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="agreeTerms"
            valuePropName="checked"
            rules={[
              {
                validator: (_, value) =>
                  value
                    ? Promise.resolve()
                    : Promise.reject(new Error('请同意服务条款和隐私政策')),
              },
            ]}
          >
            <Checkbox>
              我已阅读并同意{' '}
              <Link to="/terms" style={{ color: '#667eea' }}>
                服务条款
              </Link>{' '}
              和{' '}
              <Link to="/privacy" style={{ color: '#667eea' }}>
                隐私政策
              </Link>
            </Checkbox>
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
              注册
            </Button>
          </Form.Item>
        </Form>

        <Divider style={{ margin: '20px 0' }}>或者</Divider>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">已有账户？</Text>
          <Link
            to="/login"
            style={{
              color: '#667eea',
              fontWeight: 'bold',
              marginLeft: '8px',
            }}
          >
            立即登录
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

export default Register;