import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import Book from "@/pages/Book";
import Report from "@/pages/Report";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/books/:bookId" element={<Book />} />
        <Route path="/reports/:bookId" element={<Report />} />
      </Routes>
    </Router>
  );
}
