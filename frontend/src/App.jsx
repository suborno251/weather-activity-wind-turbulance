import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Decision from "./pages/Decision.jsx";
import Accuracy from "./pages/Accuracy.jsx";
import Method from "./pages/Method.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Decision />} />
        <Route path="accuracy" element={<Accuracy />} />
        <Route path="method" element={<Method />} />
      </Route>
    </Routes>
  );
}
