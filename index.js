const express = require('express');
const multer = require('multer');
const cors = require('cors');
const pinataSDK = require('@pinata/sdk');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Initialize Pinata SDK using API Key and Secret
const pinata = new pinataSDK({
  pinataApiKey: process.env.PINATA_API_KEY,
  pinataSecretApiKey: process.env.PINATA_SECRET_API_KEY,
  // Alternatively, use pinataJWTKey: process.env.PINATA_JWT for JWT-based authentication
});

const app = express();

// Enable CORS for all routes
app.use(cors({
  origin: '*', // You can restrict this to specific domains if necessary
  methods: ['GET', 'POST'], // Specify allowed HTTP methods
}));

// Multer setup for handling file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadsDir = path.join(__dirname, 'uploads');
    if (!fs.existsSync(uploadsDir)) {
      fs.mkdirSync(uploadsDir);
    }
    cb(null, uploadsDir);
  },
  filename: (req, file, cb) => {
    cb(null, file.originalname);
  }
});

const upload = multer({ storage: storage });

// Route for file upload
app.post('/upload', upload.single('file'), (req, res) => {
  const filePath = req.file.path;
  const readableStreamForFile = fs.createReadStream(filePath);

  const options = {
    pinataMetadata: {
      name: req.file.originalname
    },
    pinataOptions: {
      cidVersion: 0
    }
  };

  // Upload file to Pinata
  pinata.pinFileToIPFS(readableStreamForFile, options)
    .then((result) => {
      console.log('Upload successful:', result);
      res.json(result); // Return the CID and other metadata
    })
    .catch((error) => {
      console.error('Error uploading to Pinata:', error);
      res.status(500).json({ error: 'File upload failed' });
    });
});

// Start the server
app.listen(3000, () => {
  console.log('Server is running on http://localhost:3000');
});
