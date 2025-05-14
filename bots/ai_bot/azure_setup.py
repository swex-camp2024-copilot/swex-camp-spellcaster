from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import AmlCompute
from dotenv import load_dotenv
import os
import time

def setup_azure_ml():
    """Set up Azure ML workspace and compute cluster using environment variables."""
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment variables
    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    resource_group = os.getenv('AZURE_RESOURCE_GROUP')
    workspace_name = os.getenv('AZURE_WORKSPACE_NAME')
    
    if not all([subscription_id, resource_group, workspace_name]):
        raise ValueError(
            "Missing required environment variables. Please ensure AZURE_SUBSCRIPTION_ID, "
            "AZURE_RESOURCE_GROUP, and AZURE_WORKSPACE_NAME are set in your .env file."
        )
    
    # Connect to Azure ML workspace
    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name
    )
    
    # Define compute cluster configuration
    compute_name = "spellcaster-cpu"
    
    try:
        # Try to get existing compute target
        compute_cluster = ml_client.compute.get(compute_name)
        print(f"Using existing compute cluster: {compute_name}")
        
    except Exception:
        print(f"Creating new compute cluster: {compute_name}")
        
        # Define compute
        compute_cluster = AmlCompute(
            name=compute_name,
            type="amlcompute",
            size="Standard_DS2_v2",
            tier="Dedicated",
            min_instances=0,
            max_instances=4,
            idle_time_before_scale_down=120,
            enable_node_public_ip=True
        )
        
        # Create compute target
        ml_client.begin_create_or_update(compute_cluster).result()
    
    return ml_client, compute_cluster

if __name__ == "__main__":
    try:
        ml_client, compute = setup_azure_ml()
        print(f"Successfully set up compute cluster: {compute.name}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}") 