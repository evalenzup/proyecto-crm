// Shared hook: email modal state used by useFacturasList and usePagosList
import { useState } from 'react';

export const useEmailModal = <TRow = unknown>() => {
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [emailRow, setEmailRow] = useState<TRow | null>(null);
  const [emailLoading, setEmailLoading] = useState(false);

  const abrirEmailModal = (row: TRow) => {
    setEmailRow(row);
    setEmailModalOpen(true);
  };

  const cerrarEmailModal = () => {
    setEmailModalOpen(false);
    setEmailRow(null);
  };

  return {
    emailModalOpen,
    emailRow,
    emailLoading,
    setEmailLoading,
    abrirEmailModal,
    cerrarEmailModal,
  };
};
