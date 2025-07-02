import { useEffect, useState } from "react";
import axios from "axios";
import { Pencil, Trash } from "lucide-react";
import PageMeta from "../components/common/PageMeta";
import PageBreadcrumb from "../components/common/PageBreadCrumb";
import ComponentCard from "../components/common/ComponentCard";

export default function ClientesPage() {
  const [clientes, setClientes] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [open, setOpen] = useState(false);
  const [editando, setEditando] = useState(false);
  const [clienteId, setClienteId] = useState(null);
  const [form, setForm] = useState({
    nombre_razon_social: "",
    tipo_identificacion: "",
    numero_identificacion: "",
    direccion: "",
    telefono: "",
    email: "",
  });

  useEffect(() => {
    fetchClientes();
  }, []);

const fetchClientes = () => {
  axios
    .get(`${import.meta.env.VITE_API_URL}/clientes/`)
    .then((res) => {
      console.log("Respuesta backend:", res.data);
      if (Array.isArray(res.data)) {
        setClientes(res.data);
      } else {
        console.warn("La respuesta no es un array:", res.data);
        setClientes([]); // fallback para evitar el error
      }
    })
    .catch((err) => {
      console.error("Error al obtener clientes:", err);
      setClientes([]); // fallback en caso de error
    });
};

  const handleGuardar = () => {
    const method = editando ? "put" : "post";
    const url = editando
      ? `${import.meta.env.VITE_API_URL}/clientes/${clienteId}`
      : `${import.meta.env.VITE_API_URL}/clientes/`;
    axios[method](url, form)
      .then(() => {
        setOpen(false);
        resetForm();
        fetchClientes();
      })
      .catch((err) => console.error(err));
  };

  const handleEditar = (cliente) => {
    setForm({ ...cliente });
    setClienteId(cliente.id);
    setEditando(true);
    setOpen(true);
  };

  const handleEliminar = (id) => {
    if (confirm("¿Deseas eliminar este cliente?")) {
      axios
        .delete(`${import.meta.env.VITE_API_URL}/clientes/${id}`)
        .then(() => fetchClientes())
        .catch((err) => console.error(err));
    }
  };

  const resetForm = () => {
    setForm({
      nombre_razon_social: "",
      tipo_identificacion: "",
      numero_identificacion: "",
      direccion: "",
      telefono: "",
      email: "",
    });
    setEditando(false);
    setClienteId(null);
  };

const clientesFiltrados = (clientes || []).filter(
  (c) => c.nombre_razon_social?.toLowerCase().includes(busqueda.toLowerCase())
);

  return (
    <>
      <PageMeta
        title="Clientes | CRM Facturación"
        description="Gestión de clientes para el CRM de facturación."
      />
      <PageBreadcrumb pageTitle="Clientes" />
      <ComponentCard title="Listado de Clientes">
        <div className="flex justify-between mb-4">
          <input
            type="text"
            placeholder="Buscar cliente..."
            className="border border-gray-300 rounded px-3 py-2 text-sm"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
          <button
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            onClick={() => {
              resetForm();
              setOpen(true);
            }}
          >
            + Nuevo Cliente
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-200 text-sm">
            <thead className="bg-gray-100 text-left">
              <tr>
                <th className="p-3 font-medium">Razón Social</th>
                <th className="p-3 font-medium">Identificación</th>
                <th className="p-3 font-medium">Email</th>
                <th className="p-3 font-medium">Teléfono</th>
                <th className="p-3 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {clientesFiltrados.map((cliente) => (
                <tr key={cliente.id} className="border-t hover:bg-gray-50">
                  <td className="p-3">{cliente.nombre_razon_social}</td>
                  <td className="p-3">
                    {cliente.tipo_identificacion} {cliente.numero_identificacion}
                  </td>
                  <td className="p-3">{cliente.email}</td>
                  <td className="p-3">{cliente.telefono}</td>
                  <td className="p-3 flex gap-2">
                    <button
                      onClick={() => handleEditar(cliente)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      onClick={() => handleEliminar(cliente.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <Trash size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ComponentCard>

      {open && (
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-md w-full max-w-lg shadow-lg">
            <h2 className="text-xl font-semibold mb-4">
              {editando ? "Editar Cliente" : "Nuevo Cliente"}
            </h2>
            <form className="space-y-4">
              {[
                ["nombre_razon_social", "Razón Social"],
                ["tipo_identificacion", "Tipo Identificación"],
                ["numero_identificacion", "Número Identificación"],
                ["direccion", "Dirección"],
                ["telefono", "Teléfono"],
                ["email", "Email"],
              ].map(([campo, label]) => (
                <div key={campo}>
                  <label className="block text-sm font-medium mb-1">{label}</label>
                  <input
                    value={form[campo]}
                    onChange={(e) =>
                      setForm({ ...form, [campo]: e.target.value })
                    }
                    className="w-full border border-gray-300 px-3 py-2 rounded text-sm"
                  />
                </div>
              ))}
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="px-4 py-2 border rounded-md text-gray-700 hover:bg-gray-100"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleGuardar}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                >
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}