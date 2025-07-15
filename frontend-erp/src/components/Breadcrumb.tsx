// src/components/Breadcrumbs.tsx
import React from 'react';
import { Breadcrumb } from 'antd';
import Link from 'next/link';
import { useRouter } from 'next/router';
import type { ReactNode } from 'react';

interface Crumb {
  path?: string;
  label: string;
  icon?: ReactNode;
}

interface Props {
  items?: Crumb[]; // opcional: si no se pasa, se puede inferir con router
}

export const Breadcrumbs: React.FC<Props> = ({ items }) => {
  const router = useRouter();

  // Si no se pasan explícitamente los items, se generan desde la ruta
  const inferredItems: Crumb[] = router.pathname
    .split('/')
    .filter(Boolean)
    .map((segment, idx, arr) => {
      const path = '/' + arr.slice(0, idx + 1).join('/');
      const label = segment.charAt(0).toUpperCase() + segment.slice(1);
      return { path, label };
    });

  const finalItems = items ?? [{ path: '/', label: 'Inicio' }, ...inferredItems];

  return (
    <Breadcrumb
      items={finalItems.map(({ path, label, icon }) => ({
        title: path ? <Link href={path}>{icon} {label}</Link> : <>{icon} {label}</>,
      }))}
    />
  );
};
