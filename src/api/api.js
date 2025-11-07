// ===============================================
// ✅ API service for Listro (Cloud Run Ready)
// ===============================================

// Use environment variables for backend URLs
const NODE_BACKEND_URL = import.meta.env.VITE_NODE_BACKEND_URL;
const PYTHON_BACKEND_URL = import.meta.env.VITE_PYTHON_BACKEND_URL;

// Default fallback (local dev safety)
const API_BASE_URL = NODE_BACKEND_URL;


// =======================
// Sheet / Scraper APIs
// =======================

// Fetch all sheet data from the API
export const fetchSheetData = async () => {
  console.log('Fetching sheet data from API...');
  try {
    const response = await fetch(`${API_BASE_URL}/api/sheet-data`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error || 'Failed to fetch sheet data');
    if (!data.success) throw new Error(data.error || 'API returned error');

    return data;
  } catch (error) {
    console.error('Error fetching sheet data:', error);
    throw new Error(`Failed to fetch data: ${error.message}`);
  }
};

// Fetch golden sheet data from the API (for ComparisonSetupPage filters and URL)
export const fetchGoldenSheetData = async () => {
  console.log('Fetching golden sheet data from API...');
  try {
    const response = await fetch(`${API_BASE_URL}/api/golden-sheet-data`);
    const data = await response.json();

    if (!response.ok) throw new Error(data.error || 'Failed to fetch golden sheet data');
    if (!data.success) throw new Error(data.error || 'API returned error');

    console.log('✅ Golden sheet data fetched successfully:', {
      totalRows: data.totalRows,
      fromCache: data.fromCache,
      headers: data.headers,
    });

    return data;
  } catch (error) {
    console.error('Error fetching golden sheet data:', error);
    throw new Error(`Failed to fetch golden sheet data: ${error.message}`);
  }
};

// Scrape product data from a given URL
export const scrapeProductFromUrl = async (productUrl) => {
  console.log('🔍 Scraping product data from URL:', productUrl);
  try {
    const response = await fetch(`${API_BASE_URL}/api/scrape-product`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: productUrl }),
    });

    const responseData = await response.json();

    if (!response.ok) throw new Error(responseData.error || 'Failed to scrape product data');
    if (!responseData.success) throw new Error(responseData.error || 'Scraping failed');

    let productData;
    if (responseData.product) productData = responseData;
    else if (responseData.data?.data?.data) productData = responseData.data.data.data;
    else if (responseData.data?.data) productData = responseData.data.data;
    else if (responseData.data?.basic_information) productData = responseData.data;
    else if (responseData.data) productData = responseData.data;
    else productData = responseData;

    if (!productData) throw new Error('No product data found in response');

    console.log('📦 Raw scraped data:', productData);

    const safeGet = (obj, path, defaultValue = null) => {
      try {
        return path.split('.').reduce((acc, part) => acc?.[part], obj) ?? defaultValue;
      } catch {
        return defaultValue;
      }
    };

    const filterValidData = (data) => {
      if (!data || typeof data !== 'object') return null;
      const filtered = {};
      Object.entries(data).forEach(([key, value]) => {
        if (value && value !== 'N/A' && value !== 'null' && value !== 'undefined') {
          filtered[key] = value;
        }
      });
      return Object.keys(filtered).length > 0 ? filtered : null;
    };

    const product = productData.product || productData;
    const details = productData.details || {};
    const raw = productData.raw || {};

    const transformedProduct = {
      asin:
        safeGet(product, 'asin') ||
        safeGet(raw, 'manufacturingDetails.ASIN') ||
        (Array.isArray(details.manufacturingDetails)
          ? details.manufacturingDetails.find((d) => d.label === 'ASIN')?.value
          : null),

      title: safeGet(product, 'title'),

      brand:
        safeGet(product, 'brand') || safeGet(raw, 'productDetails.Brand'),

      url: productUrl,

      images: (Array.isArray(product.images) ? product.images : []).filter(
        (img) => img && img.startsWith('http')
      ),

      features: (Array.isArray(details.featureBullets) ? details.featureBullets : []).filter(
        (f) => f && f !== 'N/A' && f.trim().length > 0
      ),

      description: safeGet(product, 'description'),

      productDetails: filterValidData(raw.productDetails),
      manufacturingDetails: filterValidData(raw.manufacturingDetails),
      additionalInfo: filterValidData(raw.additionalInfo),

      productDetailsArray: Array.isArray(details.productDetails)
        ? details.productDetails.filter((d) => d.value && d.value !== 'N/A')
        : [],

      manufacturingDetailsArray: Array.isArray(details.manufacturingDetails)
        ? details.manufacturingDetails.filter((d) => d.value && d.value !== 'N/A')
        : [],

      additionalInfoArray: Array.isArray(details.additionalInfo)
        ? details.additionalInfo.filter((d) => d.value && d.value !== 'N/A')
        : [],

      rawData: productData,
    };

    console.log('✅ Product data scraped and transformed successfully:', {
      title: transformedProduct.title,
      asin: transformedProduct.asin,
      brand: transformedProduct.brand,
      imageCount: transformedProduct.images.length,
    });

    return transformedProduct;
  } catch (error) {
    console.error('❌ Error scraping product:', error);
    throw new Error(`Failed to scrape product: ${error.message}`);
  }
};

// =======================
// Legacy seller data
// =======================
export const fetchSellerData = async (category) => {
  console.log(`Fetching data for category: ${category}`);
  try {
    const sheetData = await fetchSheetData();
    let filteredData = sheetData.data;

    if (category && category !== 'All Categories') {
      filteredData = sheetData.data.filter(
        (item) =>
          item.Category && item.Category.toLowerCase() === category.toLowerCase()
      );
    }

    return filteredData.map((item, index) => ({
      productID: `API-${Date.now()}-${index}`,
      productName: `${item.Category} - ${item.Subcategory} (${item.Gender}, ${item['Age Group']})`,
      category: item.Category,
      rating: (Math.random() * 2 + 3).toFixed(1),
      reviews: Math.floor(Math.random() * 10000) + 100,
      availability: 'In Stock',
      url: item.URL,
      gender: item.Gender,
      ageGroup: item['Age Group'],
      subcategory: item.Subcategory,
    }));
  } catch (error) {
    throw new Error(`Failed to fetch data for ${category}: ${error.message}`);
  }
};

// =======================
// AI: Title / Description / Image (Python backend)
// =======================

// AI text generation (title)
export const generateProductTitle = async (subcategory, productDetails) => {
  console.log('🤖 Generating AI product title with:', { subcategory, productDetails });

  try {
    const response = await fetch(`${PYTHON_BACKEND_URL}/api/generate-title-description`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subcategory, type: 'title', ...productDetails }),
    });

    const data = await response.json();
    if (!response.ok || !data.success)
      throw new Error(data.error || 'Title generation failed');

    console.log('✅ AI product title generated successfully:', data.generated_title);
    return data.generated_title;
  } catch (error) {
    console.error('❌ Error generating AI product title:', error);
    throw new Error(`Failed to generate product title: ${error.message}`);
  }
};

// AI text generation (description)
export const generateProductDescription = async (subcategory, productDetails) => {
  console.log('🤖 Generating AI product description with:', { subcategory, productDetails });

  try {
    const response = await fetch(`${PYTHON_BACKEND_URL}/api/generate-title-description`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subcategory, type: 'description', ...productDetails }),
    });

    const data = await response.json();
    if (!response.ok || !data.success)
      throw new Error(data.error || 'Description generation failed');

    console.log('✅ AI product description generated successfully:', data.generated_description);
    return data.generated_description;
  } catch (error) {
    console.error('❌ Error generating AI product description:', error);
    throw new Error(`Failed to generate product description: ${error.message}`);
  }
};

// AI image generation
export const generateAIImage = async (imageFile, styleIndex, attributes = {}) => {
  console.log('🎨 Generating AI image with:', { styleIndex, attributes });

  try {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('style_index', styleIndex.toString());
    formData.append('attributes', JSON.stringify(attributes));

    const response = await fetch(`${PYTHON_BACKEND_URL}/generate-image`, {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Server error');

    let imageUrl;
    if (data.gcs_url) imageUrl = data.gcs_url;
    else if (data.filename)
      imageUrl = `${PYTHON_BACKEND_URL}/generated_images/${data.filename}`;
    else throw new Error('No image URL returned from server');

    console.log('✅ AI image generated successfully:', imageUrl);
    return imageUrl;
  } catch (error) {
    console.error('❌ Error generating AI image:', error);
    throw new Error(`Failed to generate AI image: ${error.message}`);
  }
};

// ✅ Export base backend URL for other components (like FinalPage)
export const API_URL = NODE_BACKEND_URL || API_BASE_URL;
