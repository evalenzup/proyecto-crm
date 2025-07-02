import { useEffect, useState } from "react";
import axios from "axios";
import { Pencil, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import PageMeta from "../components/common/PageMeta";
import PageBreadcrumb from "../components/common/PageBreadCrumb";
import ComponentCard from "../components/common/ComponentCard";

export default function EmpresasPage() {
  const [empresas, setEmpresas] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const navigate = useNavigate();

  const obtenerEmpresas = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/empresas/`);
      if (Array.isArray(res.data)) {
        setEmpresas(res.data);
      } else {
        console.warn("La respuesta no es un array:", res.data);
        setEmpresas([]);
      }
    } catch (error) {
      console.error("Error al obtener empresas:", error);
      setEmpresas([]);
    }
  };

  useEffect(() => {
    obtenerEmpresas();
  }, []);

  const handleDelete = async (id) => {
    if (!confirm("¿Seguro que deseas eliminar esta empresa?")) return;
    try {
      await axios.delete(`${import.meta.env.VITE_API_URL}/empresas/${id}`);
      obtenerEmpresas();
    } catch (error) {
      console.error("Error al eliminar empresa:", error);
    }
  };

  const empresasFiltradas = (empresas || []).filter((empresa) =>
    empresa.nombre?.toLowerCase().includes(busqueda.toLowerCase())
  );

  return (
    <>
      <PageMeta
        title="Empresas | CRM Facturación"
        description="Gestión de empresas para el CRM de facturación."
      />
      <PageBreadcrumb pageTitle="Empresas" />
      <ComponentCard title="Listado de Empresas">
        <div className="flex justify-between mb-4">
          <input
            type="text"
            placeholder="Buscar empresa..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 text-sm w-full max-w-xs"
          />
          <button
            onClick={() => navigate("/empresas/nueva")}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            + Nueva Empresa
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-200 text-sm">
            <thead className="bg-gray-100 text-left">
              <tr>
                <th className="p-3 font-medium">Nombre</th>
                <th className="p-3 font-medium">RFC</th>
                <th className="p-3 font-medium">Régimen Fiscal</th>
                <th className="p-3 font-medium">Código Postal</th>
                <th className="p-3 font-medium">Teléfono</th>
                <th className="p-3 font-medium">Email</th>
                <th className="p-3 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {empresasFiltradas.map((empresa) => (
                <tr key={empresa.id} className="border-t hover:bg-gray-50">
                  <td className="p-3">{empresa.nombre}</td>
                  <td className="p-3">{empresa.rfc}</td>
                  <td className="p-3">{empresa.regimen_fiscal}</td>
                  <td className="p-3">{empresa.codigo_postal}</td>
                  <td className="p-3">{empresa.telefono}</td>
                  <td className="p-3">{empresa.email}</td>
                  <td className="p-3 flex gap-2">
                    <button
                      onClick={() => navigate(`/empresas/editar/${empresa.id}`)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      onClick={() => handleDelete(empresa.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ComponentCard>
    </>
  );
}
