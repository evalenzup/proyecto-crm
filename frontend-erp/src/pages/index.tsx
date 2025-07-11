// src/pages/index.tsx
import React from 'react';
import { Layout } from '../components/Layout';
import { Dashboard } from '../components/Dashboard';

const HomePage: React.FC = () => (
  <Layout>
    <Dashboard />
  </Layout>
);

export default HomePage;

