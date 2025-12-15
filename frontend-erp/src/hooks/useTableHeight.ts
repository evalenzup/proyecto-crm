import { useRef, useState, useEffect } from 'react';

/**
 * Hook para calcular la altura disponible para la tabla y permitir scroll.
 * @returns { containerRef, tableY }
 */
export const useTableHeight = () => {
    const ref = useRef<HTMLDivElement | null>(null);
    const [y, setY] = useState<number | undefined>(undefined);

    useEffect(() => {
        const calc = () => {
            if (!ref.current) return setY(undefined);
            const rect = ref.current.getBoundingClientRect();
            // Restamos el top y un margen inferior (e.g. 220 o ajustado)
            // Ajuste: 200px margen inferior suele funcionar para la paginación y footer
            const h = window.innerHeight - rect.top - 200;
            setY(h > 240 ? h : 240); // Mínimo 240px
        };
        calc();
        window.addEventListener('resize', calc);
        return () => window.removeEventListener('resize', calc);
    }, []);

    return { containerRef: ref, tableY: y };
};
