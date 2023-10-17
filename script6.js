// Webserver that hosts a websocket
// cmd: node server.js 
// Takes in POST request dictionary transmitted from python inference script (appendix_e1.py)

const express = require('express');
const app = express();
const path = require('path');

const http = require('http').Server(app)
const io = require('socket.io')(http);

app.use(express.static('public')); // Allows for the project to access files in 'public' folder
app.use(express.json()); // Middleware to parse JSON data in request body

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// POST api to receive pose data from UdpCmds_inference.py through localhost port 3000
app.post('/api/pose', (req, res) => {
  const { x, y, alphabet, conf } = req.body; // Parse data from the request body
  console.log(x,y,alphabet)
  if (typeof x !== 'number' || typeof y !== 'number' || !['A', 'B', 'C', 'D'].includes(alphabet)) { // Validate the received data
    return res.status(400).json({ error: 'Pose data is in an invalid format.' });
  }
  console.log('Received Pose Data:', { x, y, alphabet, conf }); // Display received pose data 
  res.json({ message: 'Received Pose Data received successfully.' }); // Send a response back to the Python script
  io.emit('pose_data',{x,y,alphabet,conf});
});

http.listen(3000, () => {
  console.log('Server is running on http://localhost:3000');
});