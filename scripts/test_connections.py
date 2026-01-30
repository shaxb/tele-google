"""
Test Meilisearch and PostgreSQL connections
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_meilisearch():
    """Test Meilisearch connection"""
    try:
        from meilisearch import Client
        
        client = Client('http://localhost:7700', 'masterKey')
        
        # Test connection by getting version
        version = client.get_version()
        print(f"✓ Meilisearch connected successfully!")
        print(f"  Version: {version['pkgVersion']}")
        
        # Test index creation
        try:
            index = client.get_index('test_index')
            print(f"  Test index exists: {index.uid}")
        except:
            # Create test index
            task = client.create_index('test_index', {'primaryKey': 'id'})
            client.wait_for_task(task.task_uid)
            print(f"  Created test index: test_index")
        
        # Test adding a document
        test_doc = {'id': 1, 'title': 'Test Document', 'content': 'This is a test'}
        index = client.get_index('test_index')
        task = index.add_documents([test_doc])
        client.wait_for_task(task.task_uid)
        print(f"  Test document indexed successfully")
        
        # Test search
        results = index.search('test')
        print(f"  Search test: found {results['estimatedTotalHits']} results")
        
        return True
        
    except Exception as e:
        print(f"✗ Meilisearch connection failed: {e}")
        return False


async def test_postgresql():
    """Test PostgreSQL connection"""
    try:
        import psycopg2
        
        # Connection parameters
        conn_params = {
            'host': '127.0.0.1',
            'port': 5433,
            'database': 'tele_google',
            'user': 'postgres',
            'password': 'postgres'
        }
        
        # Connect
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Test query
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        print(f"✓ PostgreSQL connected successfully!")
        print(f"  Version: {version.split(',')[0]}")
        
        # Test table creation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        conn.commit()
        print(f"  Test table created successfully")
        
        # Test insert
        cursor.execute("INSERT INTO test_table (name) VALUES (%s) RETURNING id", ('test_entry',))
        test_id = cursor.fetchone()[0]
        conn.commit()
        print(f"  Test data inserted successfully (id: {test_id})")
        
        # Test select
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        print(f"  Test query: found {count} rows")
        
        # Cleanup
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Make sure Docker container is running: docker ps")
        print(f"  2. Check container logs: docker logs tele-google-postgres")
        print(f"  3. Install psycopg2: pip install psycopg2-binary")
        return False


async def main():
    """Run all connection tests"""
    print("=" * 60)
    print("TESTING DOCKER SERVICES")
    print("=" * 60)
    print()
    
    print("1. Testing Meilisearch...")
    print("-" * 60)
    meili_ok = await test_meilisearch()
    print()
    
    print("2. Testing PostgreSQL...")
    print("-" * 60)
    postgres_ok = await test_postgresql()
    print()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Meilisearch: {'✓ PASS' if meili_ok else '✗ FAIL'}")
    print(f"PostgreSQL:  {'✓ PASS' if postgres_ok else '✗ FAIL'}")
    print()
    
    if meili_ok and postgres_ok:
        print("🎉 All services are ready!")
        return 0
    else:
        print("❌ Some services failed. Check the errors above.")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
