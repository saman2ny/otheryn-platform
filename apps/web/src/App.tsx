import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header, Footer } from './layouts';
import SpatialBackdrop from './components/SpatialBackdrop';
import ScrollToTop from './components/ScrollToTop';
import RouteMeta from './lib/seo';
import DisabledHintProvider from './components/DisabledHint';

// Pages
import Home from './pages/Home';
import About from './pages/About';
import Platform from './pages/Platform';
import Architecture from './pages/Architecture';
import Products from './pages/Products';
import Solutions from './pages/Solutions';
import Industries from './pages/Industries';
import Partners from './pages/Partners';
import Security from './pages/Security';
import Pricing from './pages/Pricing';
import Contact from './pages/Contact';
import Booking from './pages/Booking';
import Checkout from './pages/Checkout';
import Careers from './pages/Careers';
import Blog from './pages/Blog';
import FAQ from './pages/FAQ';
import Privacy from './pages/Privacy';
import CookiePolicy from './pages/CookiePolicy';
import Terms from './pages/Terms';

export default function App() {
  return (
    <DisabledHintProvider>
      <BrowserRouter>
      <RouteMeta />
      <ScrollToTop />
      <SpatialBackdrop />
      <div className="relative z-10 min-h-screen flex flex-col">
        <Header />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/platform" element={<Platform />} />
            <Route path="/architecture" element={<Architecture />} />
            <Route path="/products" element={<Products />} />
            <Route path="/solutions" element={<Solutions />} />
            <Route path="/industries" element={<Industries />} />
            <Route path="/partners" element={<Partners />} />
            <Route path="/security" element={<Security />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/book" element={<Booking />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route path="/careers" element={<Careers />} />
            <Route path="/blog" element={<Blog />} />
            <Route path="/faq" element={<FAQ />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/cookie-policy" element={<CookiePolicy />} />
            <Route path="/terms" element={<Terms />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
    </DisabledHintProvider>
  );
}