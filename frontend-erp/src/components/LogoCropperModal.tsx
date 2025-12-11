import React, { useEffect, useMemo, useRef, useState } from "react";
import { Modal, Button, Tooltip, Slider } from "antd";
import {
  UploadOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  RedoOutlined,
  CheckOutlined,
  CloseOutlined,
} from "@ant-design/icons";

type Props = {
  open: boolean;
  onClose: () => void;
  onConfirm: (file: File) => void;        // retorna el PNG recortado
  empresaId: string;                      // para nombrar el archivo {id}.png
  initialImage?: string | File | Blob | null;
  initialImageUrl?: string;
};

const EXPORT_W = 1000;
const EXPORT_H = 600; // 5:3

export default function LogoCropperModal({ open, onClose, onConfirm, empresaId, initialImage, initialImageUrl }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  const [imgObj, setImgObj] = useState<HTMLImageElement | null>(null);
  const [loaded, setLoaded] = useState(false);

  // transform en coordenadas del VIEWPORT (no del canvas de export)
  const [scale, setScale] = useState(1);       // multiplicador sobre baseScale (contain)
  const [tx, setTx] = useState(0);             // translate X en px (viewport)
  const [ty, setTy] = useState(0);             // translate Y en px (viewport)
  const [dragging, setDragging] = useState(false);
  const [lastPt, setLastPt] = useState<{ x: number, y: number } | null>(null);

  // margen blanco porcentual en la exportación
  const [marginPct, setMarginPct] = useState(8); // 8% por defecto

  // Datos naturales
  const natural = useMemo(() => {
    if (!imgObj) return { w: 0, h: 0 };
    return { w: imgObj.naturalWidth, h: imgObj.naturalHeight };
  }, [imgObj]);

  // Tamaño del viewport (cuadro rojo)
  const vp = useMemo(() => {
    // Forzar re-calculo cuando se abre
    if (!open) return { w: 0, h: 0 };
    const el = viewportRef.current;
    if (!el) return { w: 0, h: 0 };
    const r = el.getBoundingClientRect();
    return { w: r.width, h: r.height };
  }, [open, loaded]);

  // Cargar initialImage al abrir
  useEffect(() => {
    if (open && (initialImage || initialImageUrl) && !imgObj) {
      const src = initialImage || initialImageUrl;
      let url = "";

      if (src instanceof File || src instanceof Blob) {
        url = URL.createObjectURL(src);
      } else if (typeof src === 'string') {
        url = src;
      }

      if (url) {
        const img = new Image();
        img.onload = () => {
          setImgObj(img);
          imgRef.current = img;
          setLoaded(true);
          setScale(1);
        };
        img.onerror = () => {
          // Fallback silencioso o limpiar
          setImgObj(null);
          setLoaded(false);
        };
        img.src = url;
        // No revocamos URL aquí para mantenerla viva mientras se edita, 
        // browser limpiará blob urls al cerrar si es necesario o garbage collect.
        // Para ser puristas deberíamos limpiar si creamos nosotros el blob url.
      }
    } else if (!open) {
      // Limpiar al cerrar
      setImgObj(null);
      setLoaded(false);
    }
  }, [open, initialImage, initialImageUrl]);

  // escala base "contain": que la imagen QUEPA completa en el viewport
  const baseScale = useMemo(() => {
    if (!natural.w || !natural.h || !vp.w || !vp.h) return 1;
    return Math.min(vp.w / natural.w, vp.h / natural.h);
  }, [natural, vp]);

  // tamaño renderizado actual (en el viewport) de la imagen
  const rendered = useMemo(() => {
    const s = baseScale * scale;
    return { w: natural.w * s, h: natural.h * s };
  }, [baseScale, scale, natural]);

  // centrar al cargar
  useEffect(() => {
    if (!loaded || !vp.w || !vp.h) return;
    const nx = (vp.w - rendered.w) / 2;
    const ny = (vp.h - rendered.h) / 2;
    setTx(nx);
    setTy(ny);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, vp.w, vp.h, baseScale]);

  const chooseImage = () => fileInputRef.current?.click();

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const url = URL.createObjectURL(f);
    const img = new Image();
    img.onload = () => {
      setImgObj(img);
      imgRef.current = img;
      setLoaded(true);
      setScale(1);
    };
    img.onerror = () => {
      setLoaded(false);
      setImgObj(null);
    };
    img.src = url;
  };

  const reset = () => {
    setScale(1);
    if (vp.w && vp.h && natural.w && natural.h) {
      const w = natural.w * baseScale;
      const h = natural.h * baseScale;
      setTx((vp.w - w) / 2);
      setTy((vp.h - h) / 2);
    } else {
      setTx(0);
      setTy(0);
    }
  };

  const zoom = (factor: number) => {
    // zoom alrededor del centro del viewport
    const oldS = baseScale * scale;
    const newScale = Math.max(0.2, Math.min(6, scale * factor));
    const newS = baseScale * newScale;

    // mantén el centro aparente
    const cx = vp.w / 2;
    const cy = vp.h / 2;

    // punto en la imagen que estaba en el centro
    const imgX = (cx - tx) / oldS;
    const imgY = (cy - ty) / oldS;

    const newTx = cx - imgX * newS;
    const newTy = cy - imgY * newS;

    setScale(newScale);
    setTx(newTx);
    setTy(newTy);
  };

  const onPointerDown = (e: React.PointerEvent) => {
    setDragging(true);
    setLastPt({ x: e.clientX, y: e.clientY });
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging || !lastPt) return;
    const dx = e.clientX - lastPt.x;
    const dy = e.clientY - lastPt.y;
    setTx((prev) => prev + dx);
    setTy((prev) => prev + dy);
    setLastPt({ x: e.clientX, y: e.clientY });
  };
  const onPointerUp = (e: React.PointerEvent) => {
    setDragging(false);
    setLastPt(null);
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
  };

  const confirm = async () => {
    if (!imgObj || !vp.w || !vp.h) return;

    // canvas de exportación
    const c = document.createElement("canvas");
    c.width = EXPORT_W;
    c.height = EXPORT_H;
    const ctx = c.getContext("2d")!;
    // fondo blanco
    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, EXPORT_W, EXPORT_H);

    // margen en px (en export)
    const m = Math.max(0, Math.min(20, marginPct));
    const mx = Math.round((m / 100) * EXPORT_W);
    const my = Math.round((m / 100) * EXPORT_H);
    const innerW = EXPORT_W - mx * 2;
    const innerH = EXPORT_H - my * 2;

    // mapeo: viewport → inner rect
    ctx.save();
    ctx.translate(mx, my);
    const k = innerW / vp.w; // == innerH / vp.h (misma relación 5:3)
    ctx.scale(k, k);

    // dibuja la imagen con la misma transform que ves en pantalla
    const s = baseScale * scale; // px viewport por px imagen
    ctx.drawImage(imgObj, tx, ty, natural.w * s, natural.h * s);
    ctx.restore();

    // exportar a File
    const blob: Blob = await new Promise((res) => c.toBlob((b) => res(b as Blob), "image/png"));
    const file = new File([blob], `${empresaId}.png`, { type: "image/png" });
    onConfirm(file);
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={980}
      destroyOnClose
      title="Editar logo (recorte 5:3)"
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 16, alignItems: "stretch" }}>
        {/* Viewport con relación 5:3 */}
        <div
          ref={viewportRef}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          style={{
            position: "relative",
            width: "100%",
            aspectRatio: "5 / 3",
            background: "#111",
            border: "3px solid #ff5b5b",
            borderRadius: 12,
            overflow: "hidden",
            cursor: dragging ? "grabbing" : "grab",
            userSelect: "none",
          }}
        >
          {imgObj && (
            <img
              src={imgObj.src}
              alt="logo"
              draggable={false}
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                transform: `translate(${tx}px, ${ty}px) scale(${baseScale * scale})`,
                transformOrigin: "top left",
                willChange: "transform",
                pointerEvents: "none",
              }}
            />
          )}
        </div>

        {/* Controles */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={onFile}
            style={{ display: "none" }}
          />

          <Button block icon={<UploadOutlined />} onClick={chooseImage}>
            Elegir imagen…
          </Button>

          <div style={{ display: "flex", gap: 8 }}>
            <Tooltip title="Alejar">
              <Button icon={<ZoomOutOutlined />} onClick={() => zoom(0.9)} />
            </Tooltip>
            <Tooltip title="Acercar">
              <Button icon={<ZoomInOutlined />} onClick={() => zoom(1.1)} />
            </Tooltip>
            <Tooltip title="Reiniciar">
              <Button icon={<RedoOutlined />} onClick={reset} />
            </Tooltip>
          </div>

          <div>
            <div style={{ fontSize: 12, color: "#888", marginBottom: 4 }}>
              Relación fija 5:3 (2.5″ × 1.5″ del PDF). Exporta a 1000×600 px, PNG.
            </div>
            <div style={{ fontSize: 12, color: "#888" }}>Margen blanco (exportación)</div>
            <Slider
              min={0}
              max={20}
              value={marginPct}
              onChange={(v) => setMarginPct(v as number)}
              marks={{ 0: "0%", 10: "10%", 20: "20%" }}
            />
          </div>

          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={confirm}
            disabled={!imgObj}
            block
          >
            Confirmar recorte
          </Button>
          <Button danger icon={<CloseOutlined />} onClick={onClose} block>
            Cancelar
          </Button>
        </div>
      </div>
    </Modal>
  );
}