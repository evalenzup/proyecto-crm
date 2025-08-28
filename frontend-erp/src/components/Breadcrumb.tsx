// src/components/Breadcrumb.tsx
import React from 'react';
import { Breadcrumb as AntdBreadcrumb } from 'antd';
import Link from 'next/link';
import { useRouter } from 'next/router';
import type { ReactNode } from 'react';

export interface Breadcrumb {
  path?: string;
  label: string;
  icon?: ReactNode;
}

interface Props {
  items?: Breadcrumb[]; // opcional: si no se pasa, se puede inferir con router
}

export const Breadcrumbs: React.FC<Props> = ({ items }) => {
  const router = useRouter();

  // Si no se pasan explícitamente los items, se generan desde la ruta
  const inferredItems: Breadcrumb[] = router.pathname
    .split('/')
    .filter(Boolean)
    .map((segment, idx, arr) => {
      const path = '/' + arr.slice(0, idx + 1).join('/');
      const label = segment.charAt(0).toUpperCase() + segment.slice(1);
      return { path, label };
    });

  const finalItems = items ?? [{ path: '/', label: 'Inicio' }, ...inferredItems];

  return (
    <AntdBreadcrumb
      items={finalItems.map(({ path, label, icon }) => ({
        title: path ? <Link href={path}>{icon} {label}</Link> : <>{icon} {label}</>,
      }))}
    />
  );
};
