export const formatDate = (iso: string) => {
    const utc = iso.endsWith('Z') ? iso : `${iso}Z`;
    return new Date(utc).toLocaleString('es-MX', {
      timeZone: 'America/Tijuana',
      dateStyle: 'short',
      timeStyle: 'medium',
    });
  };