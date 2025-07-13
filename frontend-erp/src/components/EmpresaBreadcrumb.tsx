// src/components/EmpresaBreadcrumb.tsx
import React from 'react';
import { Breadcrumb } from 'antd';
import Link from 'next/link';

interface Props {
  id?: string;
}

export const EmpresaBreadcrumb: React.FC<Props> = ({ id }) => {
  const items = [
    { title: <Link href="/">Inicio</Link> },
    { title: <Link href="/empresas">Empresas</Link> },
  ];

  if (id !== undefined) {
    items.push({ title: id ? 'Editar' : 'Nueva' });
  }

  return <Breadcrumb items={items} />;
};
