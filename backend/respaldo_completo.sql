--
-- PostgreSQL database dump
--

\restrict RULDo6y17q56yZn9GGNxohpgzjsjelt5qWXS9fR8Koa7gH1aWrzFUAEhWVRQ2BQ

-- Dumped from database version 14.19 (Debian 14.19-1.pgdg13+1)
-- Dumped by pg_dump version 14.19 (Debian 14.19-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: accion_presupuesto_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.accion_presupuesto_enum AS ENUM (
    'CREADO',
    'EDITADO',
    'ENVIADO',
    'VISTO',
    'ACEPTADO',
    'RECHAZADO',
    'FACTURADO',
    'ARCHIVADO',
    'BORRADOR',
    'CADUCADO'
);


ALTER TYPE public.accion_presupuesto_enum OWNER TO postgres;

--
-- Name: categoriaegreso; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.categoriaegreso AS ENUM (
    'GASTOS_GENERALES',
    'COMPRAS',
    'SERVICIOS',
    'IMPUESTOS',
    'NOMINA',
    'ALQUILER_OFICINA',
    'MARKETING_PUBLICIDAD',
    'TELECOMUNICACIONES',
    'TRANSPORTE_VIAJES',
    'SEGUROS',
    'REPARACIONES_MANTENIMIENTO',
    'SUMINISTROS_OFICINA',
    'SERVICIOS_PROFESIONALES',
    'LICENCIAS_SOFTWARE',
    'CAPACITACION',
    'GASOLINA',
    'OTROS'
);


ALTER TYPE public.categoriaegreso OWNER TO postgres;

--
-- Name: estado_presupuesto_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.estado_presupuesto_enum AS ENUM (
    'BORRADOR',
    'ENVIADO',
    'ACEPTADO',
    'RECHAZADO',
    'CADUCADO',
    'FACTURADO',
    'ARCHIVADO'
);


ALTER TYPE public.estado_presupuesto_enum OWNER TO postgres;

--
-- Name: estatusegreso; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.estatusegreso AS ENUM (
    'PENDIENTE',
    'PAGADO',
    'CANCELADO'
);


ALTER TYPE public.estatusegreso OWNER TO postgres;

--
-- Name: estatuspago; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.estatuspago AS ENUM (
    'BORRADOR',
    'TIMBRADO',
    'CANCELADO'
);


ALTER TYPE public.estatuspago OWNER TO postgres;

--
-- Name: rolusuario; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.rolusuario AS ENUM (
    'ADMIN',
    'SUPERVISOR'
);


ALTER TYPE public.rolusuario OWNER TO postgres;

--
-- Name: tipocontacto; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.tipocontacto AS ENUM (
    'ADMINISTRATIVO',
    'COBRANZA',
    'OPERATIVO',
    'PRINCIPAL',
    'OTRO'
);


ALTER TYPE public.tipocontacto OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: cliente_empresa; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cliente_empresa (
    cliente_id uuid NOT NULL,
    empresa_id uuid NOT NULL
);


ALTER TABLE public.cliente_empresa OWNER TO postgres;

--
-- Name: clientes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.clientes (
    id uuid NOT NULL,
    nombre_comercial character varying(255) NOT NULL,
    nombre_razon_social character varying(255) NOT NULL,
    telefono text,
    email text,
    rfc character varying(13) NOT NULL,
    regimen_fiscal character varying(100) NOT NULL,
    creado_en timestamp without time zone DEFAULT now(),
    actualizado_en timestamp without time zone DEFAULT now(),
    calle character varying(100),
    numero_exterior character varying(50),
    numero_interior character varying(50),
    colonia character varying(100),
    codigo_postal character varying(10) NOT NULL,
    dias_credito integer,
    dias_recepcion integer,
    dias_pago integer,
    tamano character varying(15),
    actividad character varying(15),
    latitud double precision,
    longitud double precision
);


ALTER TABLE public.clientes OWNER TO postgres;

--
-- Name: contactos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contactos (
    id uuid NOT NULL,
    nombre character varying(255) NOT NULL,
    puesto character varying(100),
    email character varying(255),
    telefono character varying(50),
    tipo public.tipocontacto NOT NULL,
    cliente_id uuid NOT NULL
);


ALTER TABLE public.contactos OWNER TO postgres;

--
-- Name: egresos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.egresos (
    id uuid NOT NULL,
    empresa_id uuid NOT NULL,
    descripcion character varying NOT NULL,
    monto numeric(18,2) NOT NULL,
    moneda character varying(3) NOT NULL,
    fecha_egreso date NOT NULL,
    categoria public.categoriaegreso NOT NULL,
    estatus public.estatusegreso NOT NULL,
    proveedor character varying,
    path_documento character varying,
    metodo_pago character varying
);


ALTER TABLE public.egresos OWNER TO postgres;

--
-- Name: email_configs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.email_configs (
    id integer NOT NULL,
    empresa_id uuid NOT NULL,
    smtp_server character varying NOT NULL,
    smtp_port integer NOT NULL,
    smtp_user character varying NOT NULL,
    smtp_password character varying NOT NULL,
    from_address character varying NOT NULL,
    from_name character varying,
    use_tls boolean
);


ALTER TABLE public.email_configs OWNER TO postgres;

--
-- Name: email_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.email_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.email_configs_id_seq OWNER TO postgres;

--
-- Name: email_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.email_configs_id_seq OWNED BY public.email_configs.id;


--
-- Name: empresas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.empresas (
    id uuid NOT NULL,
    nombre character varying(255) NOT NULL,
    nombre_comercial character varying(255) NOT NULL,
    ruc character varying(20) NOT NULL,
    direccion text,
    telefono character varying(50),
    email character varying(100),
    rfc character varying(13) NOT NULL,
    regimen_fiscal character varying(100) NOT NULL,
    codigo_postal character varying(10) NOT NULL,
    contrasena character varying(255) NOT NULL,
    archivo_cer character varying(255),
    archivo_key character varying(255),
    creado_en timestamp without time zone DEFAULT now() NOT NULL,
    actualizado_en timestamp without time zone DEFAULT now() NOT NULL,
    logo character varying(255)
);


ALTER TABLE public.empresas OWNER TO postgres;

--
-- Name: facturas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.facturas (
    id uuid NOT NULL,
    serie character varying(10) NOT NULL,
    folio integer NOT NULL,
    empresa_id uuid NOT NULL,
    cliente_id uuid NOT NULL,
    tipo_comprobante character varying(1) NOT NULL,
    forma_pago character varying(3),
    metodo_pago character varying(3),
    uso_cfdi character varying(3),
    moneda character varying(3) NOT NULL,
    tipo_cambio numeric(18,6),
    lugar_expedicion character varying(5),
    condiciones_pago text,
    cfdi_relacionados_tipo character varying(2),
    cfdi_relacionados text,
    subtotal numeric(18,6) NOT NULL,
    descuento numeric(18,6) NOT NULL,
    impuestos_trasladados numeric(18,6) NOT NULL,
    impuestos_retenidos numeric(18,6) NOT NULL,
    total numeric(18,6) NOT NULL,
    estatus character varying(15) NOT NULL,
    cfdi_uuid character varying(36),
    fecha_timbrado timestamp without time zone,
    no_certificado character varying(20),
    no_certificado_sat character varying(20),
    sello_cfdi text,
    sello_sat text,
    fecha_pago timestamp without time zone,
    fecha_cobro timestamp without time zone,
    status_pago character varying(10) NOT NULL,
    xml_path character varying(255),
    pdf_path character varying(255),
    creado_en timestamp without time zone DEFAULT now() NOT NULL,
    actualizado_en timestamp without time zone DEFAULT now() NOT NULL,
    observaciones text,
    fecha_emision timestamp without time zone,
    rfc_proveedor_sat character varying(13),
    motivo_cancelacion character varying(2),
    folio_fiscal_sustituto character varying(36)
);


ALTER TABLE public.facturas OWNER TO postgres;

--
-- Name: facturas_detalle; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.facturas_detalle (
    id uuid NOT NULL,
    factura_id uuid NOT NULL,
    producto_servicio_id uuid,
    no_identificacion character varying(50),
    unidad character varying(20),
    clave_producto character varying(20) NOT NULL,
    clave_unidad character varying(20) NOT NULL,
    descripcion text NOT NULL,
    cantidad numeric(18,6) NOT NULL,
    valor_unitario numeric(18,6) NOT NULL,
    descuento numeric(18,6) NOT NULL,
    importe numeric(18,6) NOT NULL,
    objeto_imp character varying(2),
    base_iva numeric(18,6),
    iva_tipo_factor character varying(10),
    iva_tasa numeric(6,4),
    iva_importe numeric(18,6),
    ret_iva_base numeric(18,6),
    ret_iva_tipo_factor character varying(10),
    ret_iva_tasa numeric(6,4),
    ret_iva_importe numeric(18,6),
    ret_isr_base numeric(18,6),
    ret_isr_tipo_factor character varying(10),
    ret_isr_tasa numeric(6,4),
    ret_isr_importe numeric(18,6),
    ieps_base numeric(18,6),
    ieps_tipo_factor character varying(10),
    ieps_tasa_cuota numeric(18,6),
    ieps_importe numeric(18,6),
    creado_en timestamp without time zone DEFAULT now() NOT NULL,
    actualizado_en timestamp without time zone DEFAULT now() NOT NULL,
    tipo character varying(50),
    requiere_lote boolean,
    lote character varying(50)
);


ALTER TABLE public.facturas_detalle OWNER TO postgres;

--
-- Name: pago_documentos_relacionados; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pago_documentos_relacionados (
    id uuid NOT NULL,
    pago_id uuid NOT NULL,
    factura_id uuid NOT NULL,
    id_documento character varying NOT NULL,
    serie character varying,
    folio character varying,
    moneda_dr character varying(3) NOT NULL,
    num_parcialidad numeric(10,0) NOT NULL,
    imp_saldo_ant numeric(18,4) NOT NULL,
    imp_pagado numeric(18,4) NOT NULL,
    imp_saldo_insoluto numeric(18,4) NOT NULL,
    tipo_cambio_dr numeric(18,6),
    impuestos_dr jsonb
);


ALTER TABLE public.pago_documentos_relacionados OWNER TO postgres;

--
-- Name: pagos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pagos (
    id uuid NOT NULL,
    empresa_id uuid NOT NULL,
    cliente_id uuid NOT NULL,
    serie character varying,
    folio character varying NOT NULL,
    fecha_pago timestamp without time zone NOT NULL,
    forma_pago_p character varying(2) NOT NULL,
    moneda_p character varying(3) NOT NULL,
    monto numeric(18,4) NOT NULL,
    tipo_cambio_p numeric(18,6),
    estatus public.estatuspago NOT NULL,
    uuid character varying,
    fecha_timbrado timestamp without time zone,
    cadena_original text,
    qr_url text,
    creado_en timestamp without time zone DEFAULT now() NOT NULL,
    actualizado_en timestamp without time zone DEFAULT now() NOT NULL,
    xml_path character varying(255),
    pdf_path character varying(255),
    motivo_cancelacion character varying(2),
    folio_fiscal_sustituto character varying(36),
    no_certificado character varying(20),
    no_certificado_sat character varying(20),
    sello_cfdi text,
    sello_sat text,
    rfc_proveedor_sat character varying(13)
);


ALTER TABLE public.pagos OWNER TO postgres;

--
-- Name: presupuesto_adjuntos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.presupuesto_adjuntos (
    id uuid NOT NULL,
    presupuesto_id uuid NOT NULL,
    archivo character varying NOT NULL,
    nombre character varying NOT NULL,
    tipo character varying(50),
    fecha_subida timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.presupuesto_adjuntos OWNER TO postgres;

--
-- Name: presupuesto_detalles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.presupuesto_detalles (
    id uuid NOT NULL,
    presupuesto_id uuid NOT NULL,
    producto_servicio_id uuid,
    descripcion text NOT NULL,
    cantidad numeric(18,2) NOT NULL,
    unidad character varying(50),
    precio_unitario numeric(18,2) NOT NULL,
    costo_estimado numeric(18,2),
    impuesto_estimado numeric(18,2),
    importe numeric(18,2) NOT NULL,
    margen_estimado numeric(18,2),
    tasa_impuesto numeric(10,4) NOT NULL
);


ALTER TABLE public.presupuesto_detalles OWNER TO postgres;

--
-- Name: presupuesto_eventos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.presupuesto_eventos (
    id uuid NOT NULL,
    presupuesto_id uuid NOT NULL,
    usuario_id uuid,
    accion public.accion_presupuesto_enum NOT NULL,
    comentario text,
    fecha_evento timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.presupuesto_eventos OWNER TO postgres;

--
-- Name: presupuestos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.presupuestos (
    id uuid NOT NULL,
    folio character varying NOT NULL,
    version integer NOT NULL,
    empresa_id uuid NOT NULL,
    cliente_id uuid NOT NULL,
    responsable_id uuid,
    fecha_emision date NOT NULL,
    fecha_vencimiento date,
    estado public.estado_presupuesto_enum NOT NULL,
    moneda character varying(3) NOT NULL,
    tipo_cambio numeric(10,2),
    subtotal numeric(18,2) NOT NULL,
    descuento_total numeric(18,2) NOT NULL,
    impuestos numeric(18,2) NOT NULL,
    total numeric(18,2) NOT NULL,
    condiciones_comerciales text,
    notas_internas text,
    firma_cliente character varying,
    creado_en timestamp without time zone DEFAULT now() NOT NULL,
    actualizado_en timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.presupuestos OWNER TO postgres;

--
-- Name: productos_servicios; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.productos_servicios (
    id uuid NOT NULL,
    tipo character varying(10) NOT NULL,
    clave_producto character varying(20) NOT NULL,
    clave_unidad character varying(20) NOT NULL,
    descripcion text NOT NULL,
    cantidad numeric(18,2),
    valor_unitario numeric(18,2) NOT NULL,
    empresa_id uuid NOT NULL,
    stock_actual numeric(18,2),
    stock_minimo numeric(18,2),
    unidad_inventario character varying(20),
    ubicacion character varying(100),
    requiere_lote boolean,
    creado_en timestamp without time zone DEFAULT now() NOT NULL,
    actualizado_en timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.productos_servicios OWNER TO postgres;

--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usuarios (
    id uuid NOT NULL,
    email character varying NOT NULL,
    hashed_password character varying NOT NULL,
    nombre_completo character varying,
    rol public.rolusuario NOT NULL,
    is_active boolean,
    empresa_id uuid
);


ALTER TABLE public.usuarios OWNER TO postgres;

--
-- Name: email_configs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.email_configs ALTER COLUMN id SET DEFAULT nextval('public.email_configs_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
2d2bc3db3f3e
\.


--
-- Data for Name: cliente_empresa; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cliente_empresa (cliente_id, empresa_id) FROM stdin;
22297d5c-75a4-4e46-8437-81ba2d90069f	f24b5d16-c9f6-413d-bd65-dcfc93985367
3158aa4f-00c7-476f-937f-301730ab7e15	f24b5d16-c9f6-413d-bd65-dcfc93985367
75a0d4a1-426e-4f31-a235-503d1fc7739f	f24b5d16-c9f6-413d-bd65-dcfc93985367
22297d5c-75a4-4e46-8437-81ba2d90069f	59b220bc-c159-4029-9400-ffac98188297
\.


--
-- Data for Name: clientes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.clientes (id, nombre_comercial, nombre_razon_social, telefono, email, rfc, regimen_fiscal, creado_en, actualizado_en, calle, numero_exterior, numero_interior, colonia, codigo_postal, dias_credito, dias_recepcion, dias_pago, tamano, actividad, latitud, longitud) FROM stdin;
3158aa4f-00c7-476f-937f-301730ab7e15	PUBLICO EN GENERAL	PUBLICO EN GENERAL	6461750500	netov1@gmail.com	XAXX010101000	616	2025-10-03 17:36:21.594322	2025-10-03 17:36:21.594322	TORREON	3918	1	PIEDRAS NEGRAS	22830	0	1	10	CHICO	RESIDENCIAL	\N	\N
22297d5c-75a4-4e46-8437-81ba2d90069f	FRENOS UNICOS	HIRAM VALENZUELA DOMINGUEZ	6461768110	netov1@gmail.com,evalenzup@gmail.com	VADH7307076E4	612	2025-08-06 22:04:02.411436	2025-10-08 01:53:51.81137	PRIMERA Y PRIMER AYUNTAMIENTO	1805	\N	HIDALGO	22880	20	1	0	CHICO	COMERCIAL	31.86143692498818	-116.5914190480434
75a0d4a1-426e-4f31-a235-503d1fc7739f	Test Presupuesto	Test Presupuesto	6461750500	netov1@gmail.com	XAXX010101000	Sin obligaciones fiscales	2025-11-20 22:16:37.97614	2025-11-20 22:16:37.97614	\N	\N	\N	\N	22830	0	0	0	\N	\N	\N	\N
\.


--
-- Data for Name: contactos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contactos (id, nombre, puesto, email, telefono, tipo, cliente_id) FROM stdin;
543134bd-a1f9-474d-9bdc-a467d7ced180	Alonso Valenzuela	Compras	netov1@gmail.com	6461377239	ADMINISTRATIVO	22297d5c-75a4-4e46-8437-81ba2d90069f
\.


--
-- Data for Name: egresos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.egresos (id, empresa_id, descripcion, monto, moneda, fecha_egreso, categoria, estatus, proveedor, path_documento, metodo_pago) FROM stdin;
6dfd4c54-c745-4088-8465-cc986f12fdcf	f24b5d16-c9f6-413d-bd65-dcfc93985367	Gasolina unidad x	1000.00	MXN	2025-10-28	GASOLINA	PENDIENTE	Rudametking	egresos/174f87a5-fd02-4494-b771-9022bc5c3c6d.pdf	1
cecf70df-8a04-48f3-bd02-a3e9452f681b	59b220bc-c159-4029-9400-ffac98188297	Viaticos	1000.00	MXN	2025-12-13	TRANSPORTE_VIAJES	PENDIENTE	Oxxo	\N	03
0d99e91c-a948-41a2-8a99-0ca8a4e0f351	59b220bc-c159-4029-9400-ffac98188297	Gasolina unidad extintores	500.00	MXN	2025-11-15	GASOLINA	PAGADO	Rudametking	egresos/2bf79b6e-17fc-48f5-b6c6-d46b4de0127f.pdf	01
\.


--
-- Data for Name: email_configs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.email_configs (id, empresa_id, smtp_server, smtp_port, smtp_user, smtp_password, from_address, from_name, use_tls) FROM stdin;
1	f24b5d16-c9f6-413d-bd65-dcfc93985367	smtp.gmail.com	587	facturacionnorton@gmail.com	gAAAAABoy3E3dGKY4CHTG8473wQwIoSIIYd5mxI2sgXV7R3cJsq8BnXyouRJNkbh3jxN6ySoDhdbx-PTL2swi3vJWsus7GK9JIecgLH4jh1zvwMndXKhFZc=	facturacionnorton@gmail.com	Facturacion Norton	t
\.


--
-- Data for Name: empresas; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.empresas (id, nombre, nombre_comercial, ruc, direccion, telefono, email, rfc, regimen_fiscal, codigo_postal, contrasena, archivo_cer, archivo_key, creado_en, actualizado_en, logo) FROM stdin;
f24b5d16-c9f6-413d-bd65-dcfc93985367	AIDA GARCIA ORTEGA	NORTON FUMIGACIONES	123	TORREON 133-1, PIEDRAS NEGRAS	6461755873	nortonservicios@hotmail.com	GAOA611225II9	612	22830	CSDNORTON	f24b5d16-c9f6-413d-bd65-dcfc93985367.cer	f24b5d16-c9f6-413d-bd65-dcfc93985367.key	2025-07-28 19:19:48.775499	2025-08-23 19:11:08.650688	logos/f24b5d16-c9f6-413d-bd65-dcfc93985367.png
59b220bc-c159-4029-9400-ffac98188297	RODOLFO MUÑOZ BARBA	NORTON EXTINTORES	12345	CALLE TORREON 133-1 COL. PIEDRAS NEGRAS	6461755873	nortonextintores@hotmail.com	MUBR601024DI0	626	22830	MUBR601024	59b220bc-c159-4029-9400-ffac98188297.cer	59b220bc-c159-4029-9400-ffac98188297.key	2025-12-11 00:22:53.626695	2025-12-13 01:01:49.05731	logos/59b220bc-c159-4029-9400-ffac98188297.png
\.


--
-- Data for Name: facturas; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.facturas (id, serie, folio, empresa_id, cliente_id, tipo_comprobante, forma_pago, metodo_pago, uso_cfdi, moneda, tipo_cambio, lugar_expedicion, condiciones_pago, cfdi_relacionados_tipo, cfdi_relacionados, subtotal, descuento, impuestos_trasladados, impuestos_retenidos, total, estatus, cfdi_uuid, fecha_timbrado, no_certificado, no_certificado_sat, sello_cfdi, sello_sat, fecha_pago, fecha_cobro, status_pago, xml_path, pdf_path, creado_en, actualizado_en, observaciones, fecha_emision, rfc_proveedor_sat, motivo_cancelacion, folio_fiscal_sustituto) FROM stdin;
e3df0cc6-b16f-4af1-b69d-5de9a00eba0f	A	3	f24b5d16-c9f6-413d-bd65-dcfc93985367	22297d5c-75a4-4e46-8437-81ba2d90069f	I	3	PUE	G03	MXN	\N	22830	\N	\N	\N	100.000000	0.000000	8.000000	0.000000	108.000000	TIMBRADA	a4039591-8e5e-49e6-96f4-e2710db432c8	2025-08-23 14:35:37	\N	00001000000509846663	WBD4np6ubfnDc/RROop+knudCSGMS22KJwWc68u/zp8puCdwbY3csYjLtIM2JxqYXmIIR8wAHKBukIuuqnzjNXDUyTw8V3B1f9h5MD8EDH7Q28f0CCD8waxjrezbpktOO2tk7QmdptgAHJn83rsojhw+ARX1/tzYXAOOP9dkcHJG+ccNh5Bdv09VbSkKZTODxJxmYeJ8h0A7DNcECNEbsv+U0t/IFIb2p4tzv39rooadYmkkCHGkkWftsOqgsNFXHv7mK4PJq1xKA2+o3BrFypEAOb9M9erWd2PUVTsPqD2ENyCR/6itZ5cUIWFGRlC1HVeNeWifBkjYjuqS0cd7kQ==	j9n6hK2F2M8eo8VAXNDnhFHzXiMP25DOUMfK0vpil8TbPROxB/7taeLXzweoNsYPgj0fUphMwNxNrZxWgvKqGkDNdP0kFHDEqqkSxjukF4Q64g8Iiwg16raUpBm+escp3AbH0XlLubidqdjMHz1PZX+pgmoIs6V7/mHhEH8P+XisSy0WoMKGJ8w+eiehK+/LdIkUT2hafAdCu91HwPyxWuuN305qxZRtZT+DJVAlRuFlbNSEYd0CkopaAro1lCl2NdPoZio+YJp0QLGD2bRGTb8PDnFu56UimMmbP807WWlptRm62IiWpxL+Bk73w3Fb4zC1gpfe04NnP8Z5KuH0ng==	2025-09-13 00:15:02.314	\N	PAGADA	/data/cfdis/GAOA611225II9-A-3-a4039591-8e5e-49e6-96f4-e2710db432c8.xml	\N	2025-08-22 20:15:37.427407	2025-10-28 21:17:07.329359	Factura de prueba 	2025-08-23 10:15:37.427	LSO1306189R5	\N	\N
c8e30997-c499-492e-919a-cdf3f1106769	A	4	f24b5d16-c9f6-413d-bd65-dcfc93985367	3158aa4f-00c7-476f-937f-301730ab7e15	I	1	PUE	G03	MXN	\N	22830	\N	\N	\N	350.000000	0.000000	56.000000	0.000000	406.000000	TIMBRADA	b751f71a-f21e-4ca8-b76f-6d2481d1abf1	2025-10-28 12:12:24	\N	00001000000509846663	jp5BxZzOSBYK3/ssLbeHd6PKN6UVc1lUZ7RRkqTV6BHcWergvzKw+ckxzJYbjYtzPh7uW9ee0kxo65NwkpWDTB0ebzB1/HNVjr7kB2H7ZCaiBBvNwStF/0eFuU4nHE8UgSE2U6MbW7qE2T5MXuB6eaK1zosG++q+0nK3i5rP/q0ihAJ2x+MB/MIt0UF3SUg5d8nb6zMy38mCxPzO+N33JMcoKsfzSCsXCU1kCTQT0o3Oj+XOx5+6oStujMjJEYIaYQ637KHkh8erQvY5dvD+VkEe8ZEOr/yOqTr1xuyyb8784cM5ORK+4TMb9N8AjtpAwXLNkd9IbgGyIcGTPtZN+A==	hsB864uMLAP3Qd245DwGFDcjr+It07illB/Z91f76+uPcgkimD7Iqj8P9OZkyMilwg33G+9GSnbdEQcFV4QvjgpPqhxp9ULHi45I0whRNXGrjKyuldiVbLZtu/310SvG2yOkZcZvBN/iltviWHpbEw5/PuY8AhVzlOaFxADS+Lhj0yPSQqQ5BPZ2qt2YbmlC6yijnezlHLNs1qhavYxrCXn6nLFg8c4qWe4DArKE0cuQjWX1PuG51CodAZ8hSe5CLbrh5+ryg41DVwPJNXHR0AKeWgIVt4HFIJAPerMmQHkuSjYLLeIId91c9RZG+ktyxyyO7BuZh4XcllhFxFtGNA==	2025-10-28 22:42:37.573	2025-10-28 07:00:00	PAGADA	/data/cfdis/GAOA611225II9-A-4-b751f71a-f21e-4ca8-b76f-6d2481d1abf1.xml	\N	2025-10-28 15:43:20.312258	2025-10-28 18:26:17.657452	\N	2025-10-28 15:42:37.573	LSO1306189R5	\N	\N
f7d8fd75-177f-4191-92cf-d103e38448ec	A	2	f24b5d16-c9f6-413d-bd65-dcfc93985367	22297d5c-75a4-4e46-8437-81ba2d90069f	I	3	PUE	G03	MXN	\N	22830	\N	\N	\N	500.000000	0.000000	40.000000	0.000000	540.000000	BORRADOR	\N	\N	\N	\N	\N	\N	2025-09-10 14:00:00	2025-09-10 14:00:00	PAGADA	\N	\N	2025-08-17 19:24:05.840139	2025-08-24 16:04:49.072787	ninguna	2025-08-21 14:00:00	\N	\N	\N
e6273443-64b9-4d1b-8c83-32284043856a	A	5	f24b5d16-c9f6-413d-bd65-dcfc93985367	3158aa4f-00c7-476f-937f-301730ab7e15	I	1	PUE	G03	MXN	\N	22830	\N	\N	\N	10.000000	0.000000	0.800000	0.000000	10.800000	BORRADOR	\N	\N	\N	\N	\N	\N	2025-11-26 17:43:55.267	2025-11-26 08:00:00	NO_PAGADA	\N	\N	2025-11-26 17:44:48.641123	2025-11-26 17:44:48.641123	\N	2025-11-26 17:43:55.267	\N	\N	\N
f1d87622-9138-486d-bca0-1c70b144afe2	A	6	f24b5d16-c9f6-413d-bd65-dcfc93985367	22297d5c-75a4-4e46-8437-81ba2d90069f	I	1	PUE	G03	MXN	\N	22830	\N	\N	\N	350.000000	0.000000	28.000000	0.000000	378.000000	TIMBRADA	35e0723f-c196-4dc2-a3d3-8cb7a68b1a66	2025-12-12 18:58:22	\N	00001000000719545303	H0Ltczzn60rw32mhXkx2bt42d+I6cVtoFwglKBiqYW5ajglAtw2L3Udo+wnGS0XtHjeu8ZH9yb95ehsH17HUv4XjcHsoc9X4hvAUttUB4MUvHd4DT0PYHCeaUTJOj2py+mh7oR31FDlnwezTBpHyyzOyKan87Le5fKL/HPHc2pCVDyno/uV5sic6joc7xFfXS/BETGO1wEPX9NDPWzr3hMQkp250US/ntpqqS3Yjc7+noNT42OOUl91egaQe27BAZgf+qcz6fpUFZu5N15+ZNfQT5rgH8O5+pYuRWijna2Tdd8wK22eH1tkK85VdQYlAcxYqk2YCwckZeb9Cn6SD4g==	GqBt6uF4dMhbYx49NIPgI7nAcmcqPUKLkIRtknVy+Kkpwgkz8VTJrci9l1713HCvpKZXW/fQKGsc17M6PlLO/mpkv7Z8H44nFtBbepetkUhm0HBqV32zEZpkyaJlSXXnvVVKlZxwqT2fy3r2iBfy6YwCKwHrZjusCuJKLFfb0zBAxsQx2EX7KcPEljESgCtPkD8WEzCCHD0/9jU6k869Mt0B62S7Amnk4SfJkxePUsnQZ278AlbYe+hNfjFvqWs9Gqr5AULx10PyNmORDc5vckIFH5c5xqCk9bBazDJbmLwXQ3enlmwmTaBATnm8m45hYrhtND7aQlGaiRzLwI7XRA==	2026-01-02 04:30:47.501	2025-12-12 08:00:00	PAGADA	/data/cfdis/GAOA611225II9-A-6-35e0723f-c196-4dc2-a3d3-8cb7a68b1a66.xml	\N	2025-12-12 20:31:33.952853	2025-12-13 00:58:21.697464	\N	2025-12-13 04:30:47.501	LSO1306189R5	\N	\N
120abba1-ac49-48e2-8c53-c1397a2ce0e9	A	1	59b220bc-c159-4029-9400-ffac98188297	22297d5c-75a4-4e46-8437-81ba2d90069f	I	1	PUE	G03	MXN	\N	22830	\N	\N	\N	100.000000	0.000000	8.000000	0.000000	108.000000	TIMBRADA	7d171c17-e44f-47fe-a704-e30c8944865b	2025-12-12 19:01:55	\N	00001000000719545303	QKXBjhtlh8ZuA+9kDFW+SAbr+B9kXILJEEPCKIlNMSoVcvg1JCJd3f2f0YZp/BLN1OwcYMtDjzMSN1CiNcSWEK3UNq1/CDLVfndxa/L80WZevijGWYrQMpUdYv/1NtZmoDKlbr94UpQN8GJ5zgutp7+HQvoXRknJz5bzcCXNhQTkVWNI8TjKQajskUuXjmYg7G2pLm26qWXMs4puFQAn4IsE/EjQ1S2UwDbNm3Jch+5yeABxPiompm2nfgqMouCFbZRPTFTHkQ4X8c+O091x0yjoZgdtuzl+tP1qYl7mEn1Pahjgpvy/wqd7VypJBvYKlmaDCH8NQTwEcK9NFamiCA==	pkosef8hIMdoilAhRLB+sNQFiGU3pO2DxWmvelm/E/d0gypwpn5T4CWjT6H8D7SPvsFAtk1avNbZ5d+Uv2xCUoQo2OrX5yARUFODFoRkVzl0YPGozdQidgbbxoDJzu86mlK5pPa/5SDpOy1TdBaURTjh2SSFxARnT3C9M5/ut+GRsfa8/CWY1z/OR+NsWzjbgvG1n24aEsaF++YrEnSoCwC/r82kzKL6tvuCwPYibXf9cEKtCyUny5pjMFgOUWWBHTw0Qg+VmwEmYDaYpB+M0prwxEkl6XI0Ub4FFvPNfH0QYkALjLhwFh9U/3UaqMISzqJ7WRG0gJsm5JSHTeZVoA==	2026-01-02 20:14:48.539	2025-12-15 08:00:00	PAGADA	/data/cfdis/MUBR601024DI0-A-1-7d171c17-e44f-47fe-a704-e30c8944865b.xml	\N	2025-12-12 20:15:42.265634	2025-12-15 19:50:26.344488	\N	2025-12-13 04:14:48.539	LSO1306189R5	\N	\N
\.


--
-- Data for Name: facturas_detalle; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.facturas_detalle (id, factura_id, producto_servicio_id, no_identificacion, unidad, clave_producto, clave_unidad, descripcion, cantidad, valor_unitario, descuento, importe, objeto_imp, base_iva, iva_tipo_factor, iva_tasa, iva_importe, ret_iva_base, ret_iva_tipo_factor, ret_iva_tasa, ret_iva_importe, ret_isr_base, ret_isr_tipo_factor, ret_isr_tasa, ret_isr_importe, ieps_base, ieps_tipo_factor, ieps_tasa_cuota, ieps_importe, creado_en, actualizado_en, tipo, requiere_lote, lote) FROM stdin;
68143865-f4f0-4451-b192-c52f231f2dff	e3df0cc6-b16f-4af1-b69d-5de9a00eba0f	\N	\N	\N	72102103	E48	SERVICIO DE FUMIGACION.	1.000000	100.000000	0.000000	108.000000	02	\N	\N	0.0800	8.000000	\N	\N	0.0000	0.000000	\N	\N	0.0000	0.000000	\N	\N	\N	\N	2025-08-24 15:31:22.021771	2025-08-24 15:31:22.021771	\N	f	\N
e24a233d-3085-4e82-b989-a3094296b6b5	f7d8fd75-177f-4191-92cf-d103e38448ec	\N	\N	\N	72102103	E48	SERVICIO DE FUMIGACION	1.000000	350.000000	0.000000	378.000000	02	\N	\N	0.0800	28.000000	\N	\N	0.0000	0.000000	\N	\N	0.0000	0.000000	\N	\N	\N	\N	2025-08-24 16:04:49.072787	2025-08-24 16:04:49.072787	\N	f	\N
6be240c1-2e93-4324-879a-717e24342ed4	f7d8fd75-177f-4191-92cf-d103e38448ec	\N	\N	\N	10191500	H87	ANTEX GEL ANTI-HORMIGAS	1.000000	150.000000	0.000000	162.000000	02	\N	\N	0.0800	12.000000	\N	\N	0.0000	0.000000	\N	\N	0.0000	0.000000	\N	\N	\N	\N	2025-08-24 16:04:49.072787	2025-08-24 16:04:49.072787	\N	f	\N
b53c8153-298e-4ce9-be06-17a0b1d424d1	c8e30997-c499-492e-919a-cdf3f1106769	\N	\N	\N	72102103	E48	SERVICIO DE FUMIGACION.	1.000000	350.000000	0.000000	406.000000	02	\N	\N	0.1600	56.000000	\N	\N	0.0000	0.000000	\N	\N	0.0000	0.000000	\N	\N	\N	\N	2025-10-28 15:43:20.312258	2025-10-28 15:43:20.312258	\N	f	\N
def2c75d-2ab0-4b61-b0f8-012c9d026ccc	e6273443-64b9-4d1b-8c83-32284043856a	\N	\N	\N	72102103	E48	SERVICIO DE FUMIGACION.	1.000000	10.000000	0.000000	10.800000	02	\N	\N	0.0800	0.800000	\N	\N	0.0000	0.000000	\N	\N	0.0000	0.000000	\N	\N	\N	\N	2025-11-26 17:44:48.641123	2025-11-26 17:44:48.641123	\N	f	\N
e79fa7f1-be9c-4c73-8a98-77d0a0923793	120abba1-ac49-48e2-8c53-c1397a2ce0e9	\N	\N	\N	72101516	E48	MANTENIMIENTO A EXTINTOR DE CO2	1.000000	100.000000	0.000000	108.000000	02	\N	\N	0.0800	8.000000	\N	\N	0.0000	0.000000	\N	\N	0.0000	0.000000	\N	\N	\N	\N	2025-12-12 20:57:49.976481	2025-12-12 20:57:49.976481	\N	f	\N
cff0119a-bc72-4a9a-964e-18497f983a25	f1d87622-9138-486d-bca0-1c70b144afe2	\N	\N	\N	72102103	E48	SERVICIO DE FUMIGACION.	1.000000	350.000000	0.000000	378.000000	02	\N	\N	0.0800	28.000000	\N	\N	0.0000	0.000000	\N	\N	0.0000	0.000000	\N	\N	\N	\N	2025-12-12 20:59:56.376195	2025-12-12 20:59:56.376195	\N	f	\N
\.


--
-- Data for Name: pago_documentos_relacionados; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.pago_documentos_relacionados (id, pago_id, factura_id, id_documento, serie, folio, moneda_dr, num_parcialidad, imp_saldo_ant, imp_pagado, imp_saldo_insoluto, tipo_cambio_dr, impuestos_dr) FROM stdin;
8cd60a40-1d77-409b-95c9-05ef20d979c9	78cd6981-58ed-4458-acb4-de6b5b595b87	e3df0cc6-b16f-4af1-b69d-5de9a00eba0f	a4039591-8e5e-49e6-96f4-e2710db432c8	A	3	MXN	1	108.0000	108.0000	0.0000	\N	\N
11bab2ff-8baf-48e0-841f-b8ce73d0f065	a5c638c2-14ed-43ae-aeab-555cc920c2c8	e3df0cc6-b16f-4af1-b69d-5de9a00eba0f	a4039591-8e5e-49e6-96f4-e2710db432c8	A	3	MXN	1	108.0000	108.0000	0.0000	\N	{"traslados_dr": [{"base_dr": 100.0, "importe_dr": 8.0, "impuesto_dr": "002", "tipo_factor_dr": "Tasa", "tasa_o_cuota_dr": 0.08}], "retenciones_dr": []}
16cb3961-ff12-427c-9923-a3fac190188a	9c80800c-2f32-4da9-87a4-1ae43d5650db	120abba1-ac49-48e2-8c53-c1397a2ce0e9	7d171c17-e44f-47fe-a704-e30c8944865b	A	1	MXN	1	108.0000	108.0000	0.0000	\N	{"traslados_dr": [{"base_dr": 100.0, "importe_dr": 8.0, "impuesto_dr": "002", "tipo_factor_dr": "Tasa", "tasa_o_cuota_dr": 0.08}], "retenciones_dr": []}
\.


--
-- Data for Name: pagos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.pagos (id, empresa_id, cliente_id, serie, folio, fecha_pago, forma_pago_p, moneda_p, monto, tipo_cambio_p, estatus, uuid, fecha_timbrado, cadena_original, qr_url, creado_en, actualizado_en, xml_path, pdf_path, motivo_cancelacion, folio_fiscal_sustituto, no_certificado, no_certificado_sat, sello_cfdi, sello_sat, rfc_proveedor_sat) FROM stdin;
78cd6981-58ed-4458-acb4-de6b5b595b87	f24b5d16-c9f6-413d-bd65-dcfc93985367	22297d5c-75a4-4e46-8437-81ba2d90069f	\N	1	2025-09-20 07:00:00	3	MXN	108.0000	\N	BORRADOR	\N	\N	\N	\N	2025-09-24 00:42:45.308336	2025-10-03 18:12:38.00105	\N	\N	\N	\N	\N	\N	\N	\N	\N
a5c638c2-14ed-43ae-aeab-555cc920c2c8	f24b5d16-c9f6-413d-bd65-dcfc93985367	22297d5c-75a4-4e46-8437-81ba2d90069f	P	2	2025-10-28 20:26:11.709	3	MXN	108.0000	\N	TIMBRADO	b27b2ca9-bc1b-445c-9c13-ec1e24e38e7d	2025-10-28 21:17:07.330421	\N	\N	2025-10-28 20:26:57.941394	2025-10-28 21:17:07.329359	/data/cfdis/GAOA611225II9-P-2-b27b2ca9-bc1b-445c-9c13-ec1e24e38e7d.xml	\N	\N	\N	\N	00001000000509846663	J0WWqoW/ke8OSbC9ztvC/Im5D/iwttTZdMlRDkVFJVVfQ5fay0GEHXvX02AUrkQsL3wEENCRugVy5QxE7rkq+Dxvtx/4xuKyytytmpVBUPZ0whsqQIAlkzlwvfkGXAkWBwiSBKuu8Sv4TvDU2RCLyJSZB8HbxKIhrxfgM8ZqYWQmMFaFtDF4zlplIme/faRoSyZgmnKrkf7CKY/F4u1Mjgi44gfH3KzJkHwgFPf/nJQQC6BOdXQdYe9wrhdh+v14Mn3UAhmaofeQYGUhdugBSQwud1XybfTCdEX3CAfgwcyfLN6ZihBs06auEPQvGxdxCk3cVZsqRt2q9yHtdjeJlg==	e5sCGrDsAelhZoWl0JeL7iikBYa4Y9/lKFopkDUP4N1DQnCRg2JQ4s2zmlQQYGErBmtigYFKzjuy4DjvO7/slX467W5jcSuwcfkVqYjTm6B79IT6M5PlGdEa107oJ5Yg7EAA+uK+VWQKqWkajk4rweg8k+fRk86MbSLJioLpriGtBzr+I2NTWwF9OmtyWBV5ttYvmr44UwPTFvqLZsq4Qu3ZrJOOCi37YWC95ULq38Evx7AgNfqpgq+MY/UKFRYafAm79w3a0POiRcGLG3oC2pRs1mpB8YyEj8QrsBQ15ducNUtA8RaV0mHzEQsE6swNARtucszdcywKjJWrC57R+g==	LSO1306189R5
9c80800c-2f32-4da9-87a4-1ae43d5650db	59b220bc-c159-4029-9400-ffac98188297	22297d5c-75a4-4e46-8437-81ba2d90069f	P	1	2025-12-13 03:49:38.27	03	MXN	108.0000	\N	CANCELADO	23191a7b-9a04-4724-9179-97aeab9d0a2e	2025-12-13 03:50:07.696106	\N	\N	2025-12-13 03:50:02.552837	2025-12-15 15:33:10.125337	/data/cfdis/MUBR601024DI0-P-1-23191a7b-9a04-4724-9179-97aeab9d0a2e.xml	\N	02	\N	00001000000703895116	00001000000719545303	ilC4HY6TmzJN3bREZ1OLvHHj5Of8GYK7eQSLfCAgJf1E3mneL3wv5mIJxIv50VMQhR6hVZj8In6UYeCjPwV82+aqsPcmdYVq50f7UqTQnFDxj7ZBwF9G0UoW2vF/aDjW7j9MLQG2ltVBdiG6pTHesF80UGO6GtMeAZeGhO9jsAxbJzel7e6jVn5UhU53ljxOPx9Gv6r8iX+LBWTHJdTzwk2tenorDIlAKOuMMiq508CVDLELzGAUSZXLRlGVa7sjmvjFjiTTiGQXXKOdWxJy8qJo5oYoOKRcY7YlwkTn+CdUl94Uc0zbHsold8xPxY9W/incZb5+Sy4LrtMWQKWknw==	ScF330NM5dkWo0zzNcRWb8vIJEE/1ZJMIQTc2hmRpIx2ZqYQOEWEq9XjcsUVX4z2zYPdSZOVKVQQhGvG+QpIxRDHK6TH7pDZsd9WHBQEbjjq6EEAbiIdzEIQzY7bUbM8/+JO/7MZPUKQn+6zv2+dZlF4RJD7AZ0hAdnJA9i/ok1ID8zXtZao3X6CNel5k9wJRZ+dUp4BOVL60kVmIaprZiCLbfNlGqavWF1jNFk0M+3pIcRq2surj087nLOX7BW0dZcsxp/fGvZS/B6uLm1aN5elhP6G7jhcpx2Y6eqzeCj6CIJiH61oO7pnOypIJyparShMNo3biuayR6huxaxeSQ==	LSO1306189R5
\.


--
-- Data for Name: presupuesto_adjuntos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.presupuesto_adjuntos (id, presupuesto_id, archivo, nombre, tipo, fecha_subida) FROM stdin;
\.


--
-- Data for Name: presupuesto_detalles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.presupuesto_detalles (id, presupuesto_id, producto_servicio_id, descripcion, cantidad, unidad, precio_unitario, costo_estimado, impuesto_estimado, importe, margen_estimado, tasa_impuesto) FROM stdin;
7db5e7db-7f2b-4b90-a6e2-7349d7592f17	e6697abd-f9ff-43c2-9d9c-c624b8afcc06	\N	SERVICIO DE FUMIGACION.	1.00	\N	10000.00	\N	800.00	10000.00	\N	0.0800
2ae4b55d-7429-4dbf-a8f3-45c55f49cc90	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	SERVICIO DE FUMIGACION.	1.00	\N	15000.00	\N	1200.00	15000.00	\N	0.0800
d3612ff0-dda0-45f3-a497-dd7382436cb0	9869c0cf-900d-4cb5-af9a-c0ff22131d79	\N	SERVICIO DE FUMIGACION.	1.00	\N	14000.00	\N	1120.00	14000.00	\N	0.0800
c707e8f7-bc6a-4ceb-a252-c37bde0b3d19	79cab60b-7840-4e47-a64d-452c5593b4b1	\N	SERVICIO DE FUMIGACION.	1.00	\N	12000.00	\N	960.00	12000.00	\N	0.0800
\.


--
-- Data for Name: presupuesto_eventos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.presupuesto_eventos (id, presupuesto_id, usuario_id, accion, comentario, fecha_evento) FROM stdin;
8db2edee-9204-4312-8ec7-727893489810	e6697abd-f9ff-43c2-9d9c-c624b8afcc06	\N	EDITADO	\N	2025-11-21 21:04:54.766702
463f9902-1618-4119-9aa5-c76b782b0d1f	e6697abd-f9ff-43c2-9d9c-c624b8afcc06	\N	EDITADO	\N	2025-11-21 21:07:40.875279
e77026b0-cb8d-4cae-a713-c27aebb5031b	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	CREADO	Nueva versión 2 creada a partir de la v1	2025-11-21 21:26:34.222446
4ca2f7ef-c9a3-437f-b621-0f546312f9ac	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	ACEPTADO	El estado del presupuesto cambió a ACEPTADO	2025-11-21 21:44:07.453167
2e43cf3f-c99d-46ac-a114-3895f6183c21	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	BORRADOR	El estado del presupuesto cambió a BORRADOR	2025-11-21 21:47:01.28743
8621e7e0-7426-4fbc-8152-4a72c1e83df4	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	RECHAZADO	El estado del presupuesto cambió a RECHAZADO	2025-11-21 21:47:04.51998
4e19f470-f307-4124-b145-8f83182a8f3e	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	BORRADOR	El estado del presupuesto cambió a BORRADOR	2025-11-21 21:47:07.134161
a4ad6af8-6f69-4e1c-892f-dbab87dd2af8	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	ACEPTADO	El estado del presupuesto cambió a ACEPTADO	2025-11-21 21:53:38.143564
cfa8943b-9f51-4aaf-bae5-8adffbe14f02	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	BORRADOR	El estado del presupuesto cambió a BORRADOR	2025-11-21 21:53:41.642424
8584540b-3081-4746-bbed-ca2d6f533f6b	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	ACEPTADO	El estado del presupuesto cambió a ACEPTADO	2025-11-21 21:55:33.210882
2afcd538-c57f-4516-a8c9-b99d5f9e1921	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	BORRADOR	El estado del presupuesto cambió a BORRADOR	2025-11-21 21:55:49.913317
95eb939c-56f6-4dca-b72a-057ccc3617cf	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	ACEPTADO	Se adjuntó evidencia: 1275_Plan_de_Trabajo_2026-2029_CPCH.pdf	2025-11-21 21:59:13.231123
1e96f6d7-c9d2-4151-b863-21f718859ed4	9a1dacd9-0849-40a1-8b32-57346a1be0f9	\N	ACEPTADO	El estado del presupuesto cambió a ACEPTADO	2025-11-21 21:59:17.425434
19973953-519f-4de6-a1cb-79a7e0b5cc45	9869c0cf-900d-4cb5-af9a-c0ff22131d79	\N	CREADO	Nueva versión 3 creada a partir de la v2	2025-11-21 22:03:20.584566
04a9067b-3238-47cc-ab9c-b8b9e6770ba2	9869c0cf-900d-4cb5-af9a-c0ff22131d79	\N	ACEPTADO	Se adjuntó evidencia: CANCELACION DE CONTRATO CIC_SRMSG_AD_2025_001-evalenzu.docx	2025-11-21 22:07:44.71098
edd271df-bbee-473e-964f-cc3695c91eea	9869c0cf-900d-4cb5-af9a-c0ff22131d79	\N	ACEPTADO	Se adjuntó evidencia: acta_protesta_varado_BOAH_salida_Frontera_abr25.pdf	2025-11-21 22:07:53.917593
13250c1c-ffac-4b61-86c3-b9d167ac6193	9869c0cf-900d-4cb5-af9a-c0ff22131d79	\N	ACEPTADO	Se adjuntó/reemplazó evidencia: 1275_CGP-cv2025.pdf	2025-11-21 22:11:37.004261
f1d250a0-8529-4f00-b9c2-e7a2189a4a44	79cab60b-7840-4e47-a64d-452c5593b4b1	\N	CREADO	Nueva versión 4 creada a partir de la v3	2025-11-26 18:14:57.544692
17fa9237-0efc-467d-b6fc-4e6d7a2c3c85	79cab60b-7840-4e47-a64d-452c5593b4b1	\N	ACEPTADO	Se adjuntó/reemplazó evidencia: reporte trabajos pendientes.pdf	2025-11-26 18:15:48.735116
\.


--
-- Data for Name: presupuestos; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.presupuestos (id, folio, version, empresa_id, cliente_id, responsable_id, fecha_emision, fecha_vencimiento, estado, moneda, tipo_cambio, subtotal, descuento_total, impuestos, total, condiciones_comerciales, notas_internas, firma_cliente, creado_en, actualizado_en) FROM stdin;
e6697abd-f9ff-43c2-9d9c-c624b8afcc06	PRE-2025-0001	1	f24b5d16-c9f6-413d-bd65-dcfc93985367	3158aa4f-00c7-476f-937f-301730ab7e15	\N	2025-11-20	2025-11-30	ARCHIVADO	MXN	1.00	10000.00	0.00	800.00	10800.00	* VIGENCIA DE 10 DÍAS\n* FUMIGACION DE NAVE INDUSTRIAL	RECOMENDACIÓN 	\N	2025-11-20 22:29:01.108193	2025-11-21 21:26:34.222446
9a1dacd9-0849-40a1-8b32-57346a1be0f9	PRE-2025-0001	2	f24b5d16-c9f6-413d-bd65-dcfc93985367	3158aa4f-00c7-476f-937f-301730ab7e15	\N	2025-11-20	2025-11-30	ARCHIVADO	MXN	1.00	15000.00	0.00	1200.00	16200.00	* VIGENCIA DE 10 DÍAS\n* FUMIGACION DE NAVE INDUSTRIAL	RECOMENDACIÓN 	data/presupuestos_evidencia/9a1dacd9-0849-40a1-8b32-57346a1be0f9_evidencia.pdf	2025-11-21 21:26:34.222446	2025-11-21 22:03:20.584566
9869c0cf-900d-4cb5-af9a-c0ff22131d79	PRE-2025-0001	3	f24b5d16-c9f6-413d-bd65-dcfc93985367	3158aa4f-00c7-476f-937f-301730ab7e15	\N	2025-11-20	2025-11-30	ARCHIVADO	MXN	1.00	14000.00	0.00	1120.00	15120.00	* VIGENCIA DE 10 DÍAS\n* FUMIGACION DE NAVE INDUSTRIAL	RECOMENDACIÓN 	data/presupuestos_evidencia/9869c0cf-900d-4cb5-af9a-c0ff22131d79_evidencia.pdf	2025-11-21 22:03:20.584566	2025-11-26 18:14:57.544692
79cab60b-7840-4e47-a64d-452c5593b4b1	PRE-2025-0001	4	f24b5d16-c9f6-413d-bd65-dcfc93985367	3158aa4f-00c7-476f-937f-301730ab7e15	\N	2025-11-20	2025-11-30	ACEPTADO	MXN	1.00	12000.00	0.00	960.00	12960.00	* VIGENCIA DE 10 DÍAS\n* FUMIGACION DE NAVE INDUSTRIAL	RECOMENDACIÓN 	data/presupuestos_evidencia/79cab60b-7840-4e47-a64d-452c5593b4b1_evidencia.pdf	2025-11-26 18:14:57.544692	2025-11-26 18:15:48.735116
\.


--
-- Data for Name: productos_servicios; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.productos_servicios (id, tipo, clave_producto, clave_unidad, descripcion, cantidad, valor_unitario, empresa_id, stock_actual, stock_minimo, unidad_inventario, ubicacion, requiere_lote, creado_en, actualizado_en) FROM stdin;
d35f76bd-d042-471b-be22-b52b51885292	PRODUCTO	10191500	H87	ANTEX GEL ANTI-HORMIGAS	10.00	150.00	f24b5d16-c9f6-413d-bd65-dcfc93985367	10.00	2.00	1	ALMACÉN GENERAL	f	2025-07-28 20:28:02.055775	2025-07-28 20:28:14.247224
6876e3c1-c7f1-4600-832f-ce5ad4e7725c	SERVICIO	72102103	E48	SERVICIO DE FUMIGACION.	\N	350.00	f24b5d16-c9f6-413d-bd65-dcfc93985367	\N	\N	\N	\N	f	2025-07-28 20:23:14.820301	2025-08-19 20:44:03.480978
31e104bc-c8e3-4678-82e1-e22270aaf775	SERVICIO	72101516	E48	MANTENIMIENTO A EXTINTOR DE CO2	\N	500.00	59b220bc-c159-4029-9400-ffac98188297	0.00	\N	\N	\N	f	2025-12-11 20:04:51.649502	2025-12-11 20:04:51.649502
d35050c6-4790-42af-accb-289fa37139ca	PRODUCTO	46191601	H87	Extintor CO2 20 lbs	10.00	1200.00	59b220bc-c159-4029-9400-ffac98188297	10.00	1.00	Pieza	Almacen	f	2025-12-11 21:53:00.794242	2025-12-11 21:53:00.794242
\.


--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.usuarios (id, email, hashed_password, nombre_completo, rol, is_active, empresa_id) FROM stdin;
d3f7826d-b1c7-452d-be1a-042ffc30f892	admin@example.com	$2b$12$UhlKkLgOwzOC1LWRJ1a6Tu2IYvxRidHN5kZ.WQXz6nnidi/w2jrPu	Administrador	ADMIN	t	\N
af1dcd29-6cd0-4cd9-868c-84930ecb1b3f	supervisor@test.com	$2b$12$HIkfeXUCQlhCOALN1TyUpOH2GbzyoyEEKU5jtC7FH.iFaR7dkCShS	Usuario de Prueba Supervisor	SUPERVISOR	t	f24b5d16-c9f6-413d-bd65-dcfc93985367
9e2e41b5-13a1-4622-85c5-a5798714b15e	test@extintores.com	$2b$12$Dhx0GGTV1.7eA9QjM2GDo.blKez2UTvaWceDFGbi6HYtuwju16aFm	Prueba Exintores	SUPERVISOR	t	59b220bc-c159-4029-9400-ffac98188297
acb52161-cbc0-4c1b-912c-88aba7bea668	test@fumigaciones.com	$2b$12$rSa/pERX8/MCt4asslrBK.O7hPvMLZ5Q4CMh4ljHPMkgcoYzEEqXq	Test Fumigaciones	SUPERVISOR	t	f24b5d16-c9f6-413d-bd65-dcfc93985367
\.


--
-- Name: email_configs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.email_configs_id_seq', 1, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: cliente_empresa cliente_empresa_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cliente_empresa
    ADD CONSTRAINT cliente_empresa_pkey PRIMARY KEY (cliente_id, empresa_id);


--
-- Name: clientes clientes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_pkey PRIMARY KEY (id);


--
-- Name: contactos contactos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contactos
    ADD CONSTRAINT contactos_pkey PRIMARY KEY (id);


--
-- Name: egresos egresos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.egresos
    ADD CONSTRAINT egresos_pkey PRIMARY KEY (id);


--
-- Name: email_configs email_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.email_configs
    ADD CONSTRAINT email_configs_pkey PRIMARY KEY (id);


--
-- Name: empresas empresas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.empresas
    ADD CONSTRAINT empresas_pkey PRIMARY KEY (id);


--
-- Name: empresas empresas_ruc_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.empresas
    ADD CONSTRAINT empresas_ruc_key UNIQUE (ruc);


--
-- Name: facturas_detalle facturas_detalle_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facturas_detalle
    ADD CONSTRAINT facturas_detalle_pkey PRIMARY KEY (id);


--
-- Name: facturas facturas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facturas
    ADD CONSTRAINT facturas_pkey PRIMARY KEY (id);


--
-- Name: pago_documentos_relacionados pago_documentos_relacionados_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pago_documentos_relacionados
    ADD CONSTRAINT pago_documentos_relacionados_pkey PRIMARY KEY (id);


--
-- Name: pagos pagos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pagos
    ADD CONSTRAINT pagos_pkey PRIMARY KEY (id);


--
-- Name: presupuesto_adjuntos presupuesto_adjuntos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuesto_adjuntos
    ADD CONSTRAINT presupuesto_adjuntos_pkey PRIMARY KEY (id);


--
-- Name: presupuesto_detalles presupuesto_detalles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuesto_detalles
    ADD CONSTRAINT presupuesto_detalles_pkey PRIMARY KEY (id);


--
-- Name: presupuesto_eventos presupuesto_eventos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuesto_eventos
    ADD CONSTRAINT presupuesto_eventos_pkey PRIMARY KEY (id);


--
-- Name: presupuestos presupuestos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuestos
    ADD CONSTRAINT presupuestos_pkey PRIMARY KEY (id);


--
-- Name: productos_servicios productos_servicios_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.productos_servicios
    ADD CONSTRAINT productos_servicios_pkey PRIMARY KEY (id);


--
-- Name: productos_servicios uq_empresa_descripcion; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.productos_servicios
    ADD CONSTRAINT uq_empresa_descripcion UNIQUE (empresa_id, descripcion);


--
-- Name: facturas uq_fact_serie_folio_por_empresa; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facturas
    ADD CONSTRAINT uq_fact_serie_folio_por_empresa UNIQUE (empresa_id, serie, folio);


--
-- Name: presupuestos uq_presupuestos_folio_version_empresa; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuestos
    ADD CONSTRAINT uq_presupuestos_folio_version_empresa UNIQUE (folio, version, empresa_id);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: ix_email_configs_empresa_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_email_configs_empresa_id ON public.email_configs USING btree (empresa_id);


--
-- Name: ix_email_configs_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_email_configs_id ON public.email_configs USING btree (id);


--
-- Name: ix_facturas_cliente_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_facturas_cliente_id ON public.facturas USING btree (cliente_id);


--
-- Name: ix_facturas_detalle_claves; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_facturas_detalle_claves ON public.facturas_detalle USING btree (clave_producto, clave_unidad);


--
-- Name: ix_facturas_detalle_factura_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_facturas_detalle_factura_id ON public.facturas_detalle USING btree (factura_id);


--
-- Name: ix_facturas_detalle_no_ident; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_facturas_detalle_no_ident ON public.facturas_detalle USING btree (no_identificacion);


--
-- Name: ix_facturas_detalle_producto_servicio_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_facturas_detalle_producto_servicio_id ON public.facturas_detalle USING btree (producto_servicio_id);


--
-- Name: ix_facturas_empresa_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_facturas_empresa_id ON public.facturas USING btree (empresa_id);


--
-- Name: ix_facturas_fechas_pago; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_facturas_fechas_pago ON public.facturas USING btree (fecha_pago, fecha_cobro);


--
-- Name: ix_facturas_serie_folio; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_facturas_serie_folio ON public.facturas USING btree (serie, folio);


--
-- Name: ix_facturas_status_pago; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_facturas_status_pago ON public.facturas USING btree (status_pago);


--
-- Name: ix_pago_documentos_relacionados_factura_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_pago_documentos_relacionados_factura_id ON public.pago_documentos_relacionados USING btree (factura_id);


--
-- Name: ix_pago_documentos_relacionados_pago_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_pago_documentos_relacionados_pago_id ON public.pago_documentos_relacionados USING btree (pago_id);


--
-- Name: ix_pagos_cliente_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_pagos_cliente_id ON public.pagos USING btree (cliente_id);


--
-- Name: ix_pagos_empresa_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_pagos_empresa_id ON public.pagos USING btree (empresa_id);


--
-- Name: ix_pagos_uuid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_pagos_uuid ON public.pagos USING btree (uuid);


--
-- Name: ix_presupuesto_adjuntos_presupuesto_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_presupuesto_adjuntos_presupuesto_id ON public.presupuesto_adjuntos USING btree (presupuesto_id);


--
-- Name: ix_presupuesto_detalles_presupuesto_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_presupuesto_detalles_presupuesto_id ON public.presupuesto_detalles USING btree (presupuesto_id);


--
-- Name: ix_presupuesto_detalles_producto_servicio_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_presupuesto_detalles_producto_servicio_id ON public.presupuesto_detalles USING btree (producto_servicio_id);


--
-- Name: ix_presupuesto_eventos_presupuesto_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_presupuesto_eventos_presupuesto_id ON public.presupuesto_eventos USING btree (presupuesto_id);


--
-- Name: ix_presupuesto_eventos_usuario_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_presupuesto_eventos_usuario_id ON public.presupuesto_eventos USING btree (usuario_id);


--
-- Name: ix_presupuestos_cliente_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_presupuestos_cliente_id ON public.presupuestos USING btree (cliente_id);


--
-- Name: ix_presupuestos_empresa_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_presupuestos_empresa_id ON public.presupuestos USING btree (empresa_id);


--
-- Name: ix_presupuestos_responsable_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_presupuestos_responsable_id ON public.presupuestos USING btree (responsable_id);


--
-- Name: ix_usuarios_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_usuarios_email ON public.usuarios USING btree (email);


--
-- Name: cliente_empresa cliente_empresa_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cliente_empresa
    ADD CONSTRAINT cliente_empresa_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: cliente_empresa cliente_empresa_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cliente_empresa
    ADD CONSTRAINT cliente_empresa_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: contactos contactos_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contactos
    ADD CONSTRAINT contactos_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: egresos egresos_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.egresos
    ADD CONSTRAINT egresos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: email_configs email_configs_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.email_configs
    ADD CONSTRAINT email_configs_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: facturas facturas_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facturas
    ADD CONSTRAINT facturas_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: facturas_detalle facturas_detalle_factura_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facturas_detalle
    ADD CONSTRAINT facturas_detalle_factura_id_fkey FOREIGN KEY (factura_id) REFERENCES public.facturas(id) ON DELETE CASCADE;


--
-- Name: facturas_detalle facturas_detalle_producto_servicio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facturas_detalle
    ADD CONSTRAINT facturas_detalle_producto_servicio_id_fkey FOREIGN KEY (producto_servicio_id) REFERENCES public.productos_servicios(id);


--
-- Name: facturas facturas_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.facturas
    ADD CONSTRAINT facturas_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: pago_documentos_relacionados pago_documentos_relacionados_factura_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pago_documentos_relacionados
    ADD CONSTRAINT pago_documentos_relacionados_factura_id_fkey FOREIGN KEY (factura_id) REFERENCES public.facturas(id);


--
-- Name: pago_documentos_relacionados pago_documentos_relacionados_pago_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pago_documentos_relacionados
    ADD CONSTRAINT pago_documentos_relacionados_pago_id_fkey FOREIGN KEY (pago_id) REFERENCES public.pagos(id);


--
-- Name: pagos pagos_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pagos
    ADD CONSTRAINT pagos_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: pagos pagos_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pagos
    ADD CONSTRAINT pagos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: presupuesto_adjuntos presupuesto_adjuntos_presupuesto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuesto_adjuntos
    ADD CONSTRAINT presupuesto_adjuntos_presupuesto_id_fkey FOREIGN KEY (presupuesto_id) REFERENCES public.presupuestos(id);


--
-- Name: presupuesto_detalles presupuesto_detalles_presupuesto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuesto_detalles
    ADD CONSTRAINT presupuesto_detalles_presupuesto_id_fkey FOREIGN KEY (presupuesto_id) REFERENCES public.presupuestos(id);


--
-- Name: presupuesto_detalles presupuesto_detalles_producto_servicio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuesto_detalles
    ADD CONSTRAINT presupuesto_detalles_producto_servicio_id_fkey FOREIGN KEY (producto_servicio_id) REFERENCES public.productos_servicios(id);


--
-- Name: presupuesto_eventos presupuesto_eventos_presupuesto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuesto_eventos
    ADD CONSTRAINT presupuesto_eventos_presupuesto_id_fkey FOREIGN KEY (presupuesto_id) REFERENCES public.presupuestos(id);


--
-- Name: presupuestos presupuestos_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuestos
    ADD CONSTRAINT presupuestos_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: presupuestos presupuestos_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.presupuestos
    ADD CONSTRAINT presupuestos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: productos_servicios productos_servicios_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.productos_servicios
    ADD CONSTRAINT productos_servicios_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: usuarios usuarios_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- PostgreSQL database dump complete
--

\unrestrict RULDo6y17q56yZn9GGNxohpgzjsjelt5qWXS9fR8Koa7gH1aWrzFUAEhWVRQ2BQ

