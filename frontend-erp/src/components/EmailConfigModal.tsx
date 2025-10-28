// frontend-erp/src/components/EmailConfigModal.tsx

import React, { useEffect } from 'react';
import {
  Modal, Form, Input, Button, message, Select, Tooltip,
} from 'antd';
import { useForm } from 'antd/lib/form/Form';
import api from '@/lib/axios';
import { normalizeHttpError } from '@/utils/httpError';
import { applyFormErrors } from '@/utils/formErrors';

interface EmailConfig {
  id: string;
  empresa_id: string;
  smtp_server: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password?: string; // Opcional para lectura, ya que no se devuelve
  smtp_use_ssl: boolean;
  smtp_use_tls: boolean;
  from_address: string;
  from_name: string;
}

interface EmailConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  empresaId: string;
  existingConfig?: EmailConfig | null;
  onConfigSaved: (config: EmailConfig) => void;
}

const EmailConfigModal: React.FC<EmailConfigModalProps> = ({
  isOpen, onClose, empresaId, existingConfig, onConfigSaved,
}) => {
  const [form] = useForm();
  const [isTestingConnection, setIsTestingConnection] = React.useState(false);
  const [isConnectionTestSuccessful, setIsConnectionTestSuccessful] = React.useState(false);

  const formValues = Form.useWatch([], form);
  const smtpUser = Form.useWatch('smtp_user', form);

  useEffect(() => {
    if (isOpen) {
      if (existingConfig) {
        form.setFieldsValue({
          ...existingConfig,
          smtp_use_ssl: existingConfig.smtp_use_ssl ?? false,
          smtp_use_tls: existingConfig.smtp_use_tls ?? false,
          from_address: existingConfig.from_address ?? '',
          from_name: existingConfig.from_name ?? '',
        });
      } else {
        form.resetFields();
      }
      setIsConnectionTestSuccessful(false); // Reset test status on modal open
    }
  }, [isOpen, existingConfig, form]);

  // Auto-fill SMTP server and port based on email provider
  useEffect(() => {
    if (!smtpUser) return;

    const lowerSmtpUser = smtpUser.toLowerCase();
    let newSmtpServer = '';
    let newSmtpPort = 587; // Default port

    if (lowerSmtpUser.includes('@gmail.com')) {
      newSmtpServer = 'smtp.gmail.com';
      newSmtpPort = 587;
    } else if (lowerSmtpUser.includes('@hotmail.com') || lowerSmtpUser.includes('@outlook.com')) {
      newSmtpServer = 'smtp.office365.com'; // Hotmail/Outlook often uses Office 365 SMTP
      newSmtpPort = 587;
    }

    // Only update if the fields are currently empty or match the default initial values
    const currentSmtpServer = form.getFieldValue('smtp_server');
    const currentSmtpPort = form.getFieldValue('smtp_port');

    if (newSmtpServer && (!currentSmtpServer || currentSmtpServer === 'smtp.gmail.com' || currentSmtpServer === 'smtp.office365.com')) {
      form.setFieldsValue({ smtp_server: newSmtpServer });
    }
    if (newSmtpPort && (!currentSmtpPort || currentSmtpPort === 587)) {
      form.setFieldsValue({ smtp_port: newSmtpPort });
    }

    // Set TLS/SSL defaults
    form.setFieldsValue({ smtp_use_ssl: false, smtp_use_tls: true });
  }, [smtpUser, form]);

  // Reset test status if form values change
  useEffect(() => {
    setIsConnectionTestSuccessful(false);
  }, [formValues]);

  const handleTestConnection = async () => {
    try {
      const values = await form.validateFields();
      setIsTestingConnection(true);
      await api.post(`/empresas/${empresaId}/email-config/test-connection`, {
        smtp_server: values.smtp_server,
        smtp_port: values.smtp_port,
        smtp_user: values.smtp_user,
        smtp_password: values.smtp_password,
        use_tls: values.smtp_use_tls,
        from_address: values.from_address,
      });
      message.success('Conexión SMTP exitosa.');
      setIsConnectionTestSuccessful(true);
    } catch (error: any) {
      message.error(normalizeHttpError(error) || 'Error al probar la conexión SMTP.');
      applyFormErrors(error, form);
      setIsConnectionTestSuccessful(false);
    } finally {
      setIsTestingConnection(false);
    }
  };

  const onFinish = async (values: any) => {
    if (!isConnectionTestSuccessful && !existingConfig) {
      message.error('Debe probar la conexión SMTP antes de guardar.');
      return;
    }
    try {
      let response;
      const payload = { ...values };
      if (existingConfig) {
        response = await api.put(`/empresas/${empresaId}/email-config`, payload);
        message.success('Configuración de correo actualizada con éxito.');
      } else {
        response = await api.post(`/empresas/${empresaId}/email-config`, payload);
        message.success('Configuración de correo guardada con éxito.');
      }
      onConfigSaved(response.data);
      onClose();
    } catch (error: any) {
      message.error(normalizeHttpError(error) || 'Error al guardar la configuración de correo.');
      applyFormErrors(error, form);
    }
  };

  return (
    <Modal
      title="Configuración de Correo Electrónico"
      open={isOpen}
      onCancel={onClose}
      footer={[
        <Button key="test" onClick={handleTestConnection} loading={isTestingConnection}>
          Probar Conexión
        </Button>,
        <Button key="back" onClick={onClose}>
          Cancelar
        </Button>,
        <Button key="submit" type="primary" onClick={form.submit} disabled={!isConnectionTestSuccessful && !existingConfig}>
          Guardar
        </Button>,
      ]}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{ smtp_port: 587, smtp_use_ssl: false, smtp_use_tls: true }}
      >
          <Form.Item
            name="smtp_server"
            label="Servidor SMTP"
            tooltip="La dirección del servidor SMTP de tu proveedor de correo (ej. smtp.gmail.com)."
            rules={[{ required: true, message: 'Por favor ingresa el servidor SMTP' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="smtp_port"
            label="Puerto SMTP"
            tooltip="El puerto de conexión para el servidor SMTP (ej. 587 para TLS, 465 para SSL)."
            rules={[{ required: true, message: 'Por favor ingresa el puerto SMTP' }]}
          >
            <Input type="number" />
          </Form.Item>
          <Form.Item
            name="smtp_user"
            label="Usuario SMTP"
            tooltip="El nombre de usuario para autenticarse en el servidor SMTP, generalmente tu dirección de correo electrónico."
            rules={[{ required: true, message: 'Por favor ingresa el usuario SMTP' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="smtp_password"
            label="Contraseña SMTP"
            tooltip="La contraseña para autenticarse en el servidor SMTP. Si dejas este campo en blanco, la contraseña existente no se modificará."
            rules={[{ required: !existingConfig, message: 'Por favor ingresa la contraseña SMTP' }]}
          >
            <Input.Password placeholder={existingConfig ? "Dejar en blanco para no cambiar" : ""} />
          </Form.Item>
          <Form.Item
            name="smtp_use_ssl"
            label="Usar SSL"
            tooltip="Habilitar SSL (Secure Sockets Layer) para una conexión segura. Generalmente se usa con el puerto 465."
          >
            <Select>
              <Select.Option value={true}>Sí</Select.Option>
              <Select.Option value={false}>No</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="smtp_use_tls"
            label="Usar TLS"
            tooltip="Habilitar TLS (Transport Layer Security) para una conexión segura. Generalmente se usa con el puerto 587."
          >
            <Select>
              <Select.Option value={true}>Sí</Select.Option>
              <Select.Option value={false}>No</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="from_address"
            label="Email del Remitente"
            tooltip="La dirección de correo electrónico que aparecerá como remitente de los correos enviados por la aplicación (ej. 'tu@empresa.com')."
            rules={[{ required: true, message: 'Por favor ingresa el email del remitente' }]}
          >
            <Input type="email" />
          </Form.Item>
          <Form.Item
            name="from_name"
            label="Nombre del Remitente"
            tooltip="El nombre que aparecerá como remitente de los correos enviados por la aplicación (ej. 'Tu Empresa')."
            rules={[{ required: true, message: 'Por favor ingresa el nombre del remitente' }]}
          >
            <Input />
          </Form.Item>
      </Form>
    </Modal>
  );
};

export default EmailConfigModal;