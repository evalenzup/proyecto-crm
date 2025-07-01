import { useEffect, useState } from "react"
import axios from "axios"
import { Pencil, Trash } from "lucide-react"

export default function ClientesPage() {
  const [clientes, setClientes] = useState([])
  const [busqueda, setBusqueda] = useState("")
  const [open, setOpen] = useState(false)
  const [editando, setEditando] = useState(false)
  const [clienteId, setClienteId] = useState(null)
  const [form, setForm] = useState({
    nombre_razon_social: "",
    tipo_identificacion: "",
    numero_identificacion: "",
    direccion: "",
    telefono: "",
    email: "",
  })

  useEffect(() => {
    fetchClientes()
  }, [])

  const fetchClientes = () => {
    axios
    .get("http://localhost:8000/api/clientes/")
    .then((res) => {
      console.log("Respuesta backend:", res.data);
      setClientes(res.data); // asegúrate que `res.data` es un array
    })
    .catch((error) => console.error("Error al obtener clientes:", error));
  }

  const handleGuardar = () => {
    const method = editando ? "put" : "post"
    const url = editando ? `/api/clientes/${clienteId}` : "/api/clientes"
    axios[method](url, form)
      .then(() => {
        setOpen(false)
        resetForm()
        fetchClientes()
      })
      .catch((err) => console.error(err))
  }

  const handleEditar = (cliente) => {
    setForm({ ...cliente })
    setClienteId(cliente.id)
    setEditando(true)
    setOpen(true)
  }

  const handleEliminar = (id) => {
    if (confirm("¿Deseas eliminar este cliente?")) {
      axios
        .delete(`/api/clientes/${id}`)
        .then(() => fetchClientes())
        .catch((err) => console.error(err))
    }
  }

  const resetForm = () => {
    setForm({
      nombre_razon_social: "",
      tipo_identificacion: "",
      numero_identificacion: "",
      direccion: "",
      telefono: "",
      email: "",
    })
    setEditando(false)
    setClienteId(null)
  }

  const clientesFiltrados = clientes.filter((c) =>
    c.nombre_razon_social.toLowerCase().includes(busqueda.toLowerCase())
  )

  return (
    <div className="p-6 bg-white rounded-md shadow-md">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">Clientes</h1>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Buscar cliente..."
            className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
          <button
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            onClick={() => {
              resetForm()
              setOpen(true)
            }}
          >
            + Nuevo Cliente
          </button>
        </div>
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
              <tr key={cliente.id} className="border-t">
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

      {open && (
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-md w-full max-w-lg">
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
                  <label className="block text-sm font-medium mb-1">
                    {label}
                  </label>
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
    </div>
  )
}

