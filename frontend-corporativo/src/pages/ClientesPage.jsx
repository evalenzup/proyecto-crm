import { useEffect, useState } from "react";
import axios from "axios";
import { Pencil, Trash2, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import PageMeta from "../components/common/PageMeta";
import PageBreadcrumb from "../components/common/PageBreadCrumb";
import ComponentCard from "../components/common/ComponentCard";

export default function ClientesPage() {
  const [clientes, setClientes] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const navigate = useNavigate();

  const obtenerClientes = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/clientes/`);
      if (Array.isArray(res.data)) {
        setClientes(res.data);
      } else {
        console.warn("La respuesta no es un array:", res.data);
        setClientes([]);
      }
    } catch (error) {
      console.error("Error al obtener clientes:", error);
      setClientes([]);
    }
  };

  useEffect(() => {
    obtenerClientes();
  }, []);

  const handleDelete = async (id) => {
    if (!confirm("¿Seguro que deseas eliminar este cliente?")) return;
    try {
      await axios.delete(`${import.meta.env.VITE_API_URL}/clientes/${id}`);
      obtenerClientes();
    } catch (error) {
      console.error("Error al eliminar cliente:", error);
    }
  };

  const clientesFiltrados = (clientes || []).filter((cliente) =>
    cliente.nombre_razon_social?.toLowerCase().includes(busqueda.toLowerCase())
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
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full max-w-xs rounded-lg border border-stroke bg-transparent px-4 py-3 text-sm text-black placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-0"
          />
          <button
            onClick={() => navigate("/clientes/nuevo")}
            className="inline-flex items-center justify-center gap-2 rounded-lg transition px-4 py-3 text-sm bg-brand-500 text-white shadow-theme-xs hover:bg-brand-600 disabled:bg-brand-300"
          >
            Nuevo Cliente
            <Plus size={18} />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-boxdark text-sm rounded-lg">
            <thead className="bg-gray-100 dark:bg-gray-800">
              <tr>
                {["Razón Social", "Identificación", "Email", "Teléfono", "Acciones"].map((header) => (
                  <th key={header} className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {clientesFiltrados.length > 0 ? (
                clientesFiltrados.map((cliente) => (
                  <tr key={cliente.id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition">
                    <td className="px-4 py-2 text-gray-800 dark:text-gray-200">
                      {cliente.nombre_razon_social}
                    </td>
                    <td className="px-4 py-2 text-gray-800 dark:text-gray-200">
                      {cliente.tipo_identificacion} {cliente.numero_identificacion}
                    </td>
                    <td className="px-4 py-2 text-gray-800 dark:text-gray-200">
                      {cliente.email}
                    </td>
                    <td className="px-4 py-2 text-gray-800 dark:text-gray-200">
                      {cliente.telefono}
                    </td>
                    <td className="px-4 py-2 flex gap-2">
                      <button
                        onClick={() => navigate(`/clientes/editar/${cliente.id}`)}
                        className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        onClick={() => handleDelete(cliente.id)}
                        className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="px-4 py-4 text-center text-gray-500 dark:text-gray-400">
                    No se encontraron clientes.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </ComponentCard>
    </>
  );
}
