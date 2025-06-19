try {
  var status = rs.status();
  print('Replica set already initialized');
} catch(e) {
  print('Initializing replica set...');
  rs.initiate({
    _id: 'rs0',
    members: [{ _id: 0, host: 'localhost:27017' }]
  });
  print('Replica set initialized');
}