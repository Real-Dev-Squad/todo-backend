#!/bin/bash

# Colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Todo App Development Environment Setup ===${NC}"

# Create required directories
echo -e "${YELLOW}Creating directories for MongoDB data and logs...${NC}"
mkdir -p mongo_data
mkdir -p mongo_logs

# Stop any existing containers
echo -e "${YELLOW}Stopping any existing containers...${NC}"
docker-compose down

# Start MongoDB
echo -e "${YELLOW}Starting MongoDB container...${NC}"
docker-compose up -d db

# Wait for MongoDB to be ready
echo -e "${YELLOW}Waiting for MongoDB to initialize (this may take a moment)...${NC}"
for i in {1..30}; do
    if docker exec todo-mongo mongosh --quiet --eval "db.runCommand({ping:1}).ok" &>/dev/null; then
        echo -e "\n${GREEN}MongoDB is up and running!${NC}"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo -e "\n${RED}Timed out waiting for MongoDB to start. Check the logs:${NC}"
        docker logs todo-mongo
        exit 1
    fi
    
    echo -n "."
    sleep 2
done

# Initialize replica set
echo -e "${YELLOW}Initializing replica set...${NC}"
docker exec todo-mongo mongosh --eval '
  try {
    rs.status();
    print("Replica set already initialized");
  } catch (err) {
    if (err.codeName === "NotYetInitialized") {
      rs.initiate({
        _id: "rs0", 
        members: [
          { _id: 0, host: "localhost:27017" }
        ]
      });
      print("Initialized replica set");
    } else {
      print("Error checking replica set status: " + err);
      quit(1);
    }
  }
' || {
    echo -e "${RED}Failed to initialize replica set.${NC}"
    echo -e "${YELLOW}Checking MongoDB logs:${NC}"
    docker logs todo-mongo
    exit 1
}

# Wait for replica set to initialize
echo -e "${YELLOW}Waiting for replica set to initialize...${NC}"
for i in {1..15}; do
    RS_STATUS=$(docker exec todo-mongo mongosh --quiet --eval "try { rs.status().ok } catch(e) { 0 }")
    if [ "$RS_STATUS" == "1" ]; then
        echo -e "${GREEN}Replica set initialized successfully!${NC}"
        break
    fi
    
    if [ $i -eq 15 ]; then
        echo -e "${RED}Timed out waiting for replica set to initialize.${NC}"
        echo -e "${YELLOW}You may need to check the MongoDB logs: docker logs todo-mongo${NC}"
        exit 1
    fi
    
    echo -n "."
    sleep 2
done

# Update .env file
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Updating .env file with replica set configuration...${NC}"
    
    # Create a temporary file
    TEMP_FILE=$(mktemp)
    
    # Copy all lines except MONGODB_URI
    grep -v "MONGODB_URI=" "$ENV_FILE" > "$TEMP_FILE" || true
    
    # Add the updated MONGODB_URI
    echo "MONGODB_URI=mongodb://localhost:27017/?replicaSet=rs0" >> "$TEMP_FILE"
    
    # Replace the original file
    mv "$TEMP_FILE" "$ENV_FILE"
    
    echo -e "${GREEN}Updated MONGODB_URI in .env file.${NC}"
else
    echo -e "${YELLOW}Creating new .env file with development settings...${NC}"
    cat > "$ENV_FILE" << EOL
ENV=DEVELOPMENT
SECRET_KEY=unique-secret
ALLOWED_HOSTS=localhost,127.0.0.1
MONGODB_URI=mongodb://localhost:27017/?replicaSet=rs0
DB_NAME=todo-app
EOL
    echo -e "${GREEN}Created new .env file with development settings.${NC}"
fi

echo -e "${GREEN}=== Environment setup complete! ===${NC}"
echo -e "${YELLOW}Your .env file has been updated with the replica set configuration.${NC}"
echo -e "${YELLOW}To start your Django app, run:${NC}"
echo -e "${GREEN}python manage.py runserver${NC}"
echo -e "\n${YELLOW}Note: You only need to run this setup script once or if you reset your MongoDB container.${NC}"
echo -e "${YELLOW}For daily development, just ensure the MongoDB container is running with:${NC}"
echo -e "${GREEN}docker-compose up -d db${NC}"