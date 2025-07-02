import { useEffect, useState } from "react";
import axios from "axios";
import { Pencil, Trash2 } from "lucide-react";

export default function EmpresasPage() {
  const [empresas, setEmpresas] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [modalVisible, setModalVisible] = useState(false);
  const [empresaActual, setEmpresaActual] = useState(null);

  const [formData, setFormData] = useState({
    nombre: "",
    ruc: "",
    direccion: "",
    telefono: "",
    email: "",
    rfc: "",
    regimen_fiscal: "",
    codigo_postal: "",
  });

  const obtenerEmpresas = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/empresas/");
      setEmpresas(res.data);
    } catch (error) {
      console.error("Error al obtener empresas:", error);
    }
  };

  useEffect(() => {
    obtenerEmpresas();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (empresaActual) {
        await axios.put(
          `http://localhost:8000/api/empresas/${empresaActual.id}`,
          formData
        );
      } else {
        await axios.post("http://localhost:8000/api/empresas/", formData);
      }
      setModalVisible(false);
      setEmpresaActual(null);
      setFormData({
        nombre: "",
        ruc: "",
        direccion: "",
        telefono: "",
        email: "",
        rfc: "",
        regimen_fiscal: "",
        codigo_postal: "",
      });
      obtenerEmpresas();
    } catch (error) {
      console.error("Error al guardar empresa:", error);
    }
  };

  const handleEdit = (empresa) => {
    setEmpresaActual(empresa);
    setFormData(empresa);
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    if (!confirm("¿Seguro que deseas eliminar esta empresa?")) return;
    try {
      await axios.delete(`http://localhost:8000/api/empresas/${id}`);
      obtenerEmpresas();
    } catch (error) {
      console.error("Error al eliminar empresa:", error);
    }
  };

  const empresasFiltradas = empresas.filter((empresa) =>
    empresa.nombre.toLowerCase().includes(busqueda.toLowerCase())
  );

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-2xl font-bold">Empresas</h1>

      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Buscar empresa..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="border p-2 rounded w-full max-w-xs"
        />
        <button
          onClick={() => {
            setEmpresaActual(null);
            setFormData({
              nombre: "",
              ruc: "",
              direccion: "",
              telefono: "",
              email: "",
              rfc: "",
              regimen_fiscal: "",
              codigo_postal: "",
            });
            setModalVisible(true);
          }}
          className="bg-blue-500 text-white px-4 py-2 rounded"
        >
          + Nueva Empresa
        </button>
      </div>

      <table className="min-w-full border">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-2 text-left">Nombre</th>
            <th className="p-2 text-left">RFC</th>
            <th className="p-2 text-left">Régimen Fiscal</th>
            <th className="p-2 text-left">Código Postal</th>
            <th className="p-2 text-left">Teléfono</th>
            <th className="p-2 text-left">Email</th>
            <th className="p-2 text-left">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {empresasFiltradas.map((empresa) => (
            <tr key={empresa.id} className="border-t">
              <td className="p-2">{empresa.nombre}</td>
              <td className="p-2">{empresa.rfc}</td>
              <td className="p-2">{empresa.regimen_fiscal}</td>
              <td className="p-2">{empresa.codigo_postal}</td>
              <td className="p-2">{empresa.telefono}</td>
              <td className="p-2">{empresa.email}</td>
              <td className="p-2 flex gap-2">
                <button
                  onClick={() => handleEdit(empresa)}
                  className="text-blue-500"
                >
                  <Pencil size={18} />
                </button>
                <button
                  onClick={() => handleDelete(empresa.id)}
                  className="text-red-500"
                >
                  <Trash2 size={18} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {modalVisible && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded w-full max-w-lg">
            <h2 className="text-lg font-bold mb-4">
              {empresaActual ? "Editar Empresa" : "Nueva Empresa"}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-3">
              {[
                { name: "nombre", label: "Nombre" },
                { name: "ruc", label: "RUC" },
                { name: "direccion", label: "Dirección" },
                { name: "telefono", label: "Teléfono" },
                { name: "email", label: "Email" },
                { name: "rfc", label: "RFC" },
                { name: "regimen_fiscal", label: "Régimen Fiscal" },
                { name: "codigo_postal", label: "Código Postal" },
              ].map((field) => (
                <div key={field.name}>
                  <label className="block text-sm">{field.label}</label>
                  <input
                    type="text"
                    value={formData[field.name] || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, [field.name]: e.target.value })
                    }
                    className="border p-2 rounded w-full"
                  />
                </div>
              ))}
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setModalVisible(false)}
                  className="px-4 py-2 border rounded"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="bg-blue-500 text-white px-4 py-2 rounded"
                >
                  {empresaActual ? "Actualizar" : "Guardar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
