import logging
from enum import Enum
from typing import Sequence, Union

import mcp.types as types
from mcp.server import Server
from monday import MondayClient

from mcp_server_monday.board import (
    handle_monday_get_board_columns,
    handle_monday_get_board_groups,
    handle_monday_list_boards,
)
from mcp_server_monday.document import (
    handle_monday_get_item_updates,
    handle_monday_get_docs,
    handle_monday_get_doc_content,
    handle_monday_create_doc,
    handle_monday_add_doc_block,
    handle_monday_get_item_files,
    handle_monday_get_update_files,
)
from mcp_server_monday.item import (
    handle_monday_create_item,
    handle_monday_create_update_on_item,
    handle_monday_list_items_in_groups,
    handle_monday_list_subitems_in_items,
    handle_monday_update_item,
)

logger = logging.getLogger("mcp-server-monday")


class ToolName(str, Enum):
    LIST_BOARDS = "monday-list-boards"
    GET_BOARD_GROUPS = "monday-get-board-groups"
    GET_BOARD_COLUMNS = "monday-get-board-columns"

    CREATE_ITEM = "monday-create-item"
    UPDATE_ITEM = "monday-update-item"
    CREATE_UPDATE = "monday-create-update"
    LIST_ITEMS_IN_GROUPS = "monday-list-items-in-groups"
    LIST_SUBITEMS_IN_ITEMS = "monday-list-subitems-in-items"
    GET_ITEM_UPDATES = "monday-get-item-updates"
    
    GET_DOCS = "monday-get-docs"
    GET_DOC_CONTENT = "monday-get-doc-content"
    CREATE_DOC = "monday-create-doc"
    ADD_DOC_BLOCK = "monday-add-doc-block"
    
    GET_ITEM_FILES = "monday-get-item-files"
    GET_UPDATE_FILES = "monday-get-update-files"


ServerTools = [
    types.Tool(
        name=ToolName.CREATE_ITEM,
        description="Create a new item in a Monday.com Board. Optionally, specify the parent Item ID to create a Sub-item.",
        inputSchema={
            "type": "object",
            "properties": {
                "boardId": {
                    "type": "string",
                    "description": "Monday.com Board ID that the Item or Sub-item is on.",
                },
                "itemTitle": {
                    "type": "string",
                    "description": "Name of the Monday.com Item or Sub-item that will be created.",
                },
                "groupId": {
                    "type": "string",
                    "description": "Monday.com Board's Group ID to create the Item in. If set, parentItemId should not be set.",
                },
                "parentItemId": {
                    "type": "string",
                    "description": "Monday.com Item ID to create the Sub-item under. If set, groupId should not be set.",
                },
                "columnValues": {
                    "type": "object",
                    "description": "Dictionary of column values to set {column_id: value}",
                },
            },
            "required": ["boardId", "itemTitle"],
        },
    ),
    types.Tool(
        name=ToolName.UPDATE_ITEM,
        description="Update a Monday.com item's or sub-item's column values.",
        inputSchema={
            "type": "object",
            "properties": {
                "boardId": {
                    "type": "string",
                    "description": "Monday.com Board ID that the Item or Sub-item is on.",
                },
                "itemId": {
                    "type": "string",
                    "description": "Monday.com Item or Sub-item ID to update the columns of.",
                },
                "columnValues": {
                    "type": "object",
                    "description": "Dictionary of column values to update the Monday.com Item or Sub-item with. ({column_id: value})",
                },
            },
            "required": ["boardId", "itemId", "columnValues"],
        },
    ),
    types.Tool(
        name=ToolName.GET_BOARD_COLUMNS,
        description="Get the Columns of a Monday.com Board.",
        inputSchema={
            "type": "object",
            "properties": {
                "boardId": {
                    "type": "string",
                    "description": "Monday.com Board ID that the Item or Sub-item is on.",
                },
            },
            "required": ["boardId"],
        },
    ),
    types.Tool(
        name=ToolName.GET_BOARD_GROUPS,
        description="Get the Groups of a Monday.com Board.",
        inputSchema={
            "type": "object",
            "properties": {
                "boardId": {
                    "type": "string",
                    "description": "Monday.com Board ID that the Item or Sub-item is on.",
                },
            },
            "required": ["boardId"],
        },
    ),
    types.Tool(
        name=ToolName.CREATE_UPDATE,
        description="Create an update (comment) on a Monday.com Item or Sub-item.",
        inputSchema={
            "type": "object",
            "properties": {
                "itemId": {"type": "string"},
                "updateText": {
                    "type": "string",
                    "description": "Content to update the Item or Sub-item with.",
                },
            },
            "required": ["itemId", "updateText"],
        },
    ),
    types.Tool(
        name=ToolName.LIST_BOARDS,
        description="Get all Boards from Monday.com",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of Monday.com Boards to return.",
                }
            },
        },
    ),
    types.Tool(
        name=ToolName.LIST_ITEMS_IN_GROUPS,
        description="List all items in the specified groups of a Monday.com board",
        inputSchema={
            "type": "object",
            "properties": {
                "boardId": {
                    "type": "string",
                    "description": "Monday.com Board ID that the Item or Sub-item is on.",
                },
                "groupIds": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
            },
            "required": ["boardId", "groupIds"],
        },
    ),
    types.Tool(
        name=ToolName.LIST_SUBITEMS_IN_ITEMS,
        description="List all Sub-items of a list of Monday.com Items",
        inputSchema={
            "type": "object",
            "properties": {
                "itemIds": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["itemIds"],
        },
    ),
    types.Tool(
        name=ToolName.GET_ITEM_UPDATES,
        description="Get updates for a specific item in Monday.com",
        inputSchema={
            "type": "object",
            "properties": {
                "itemId": {
                    "type": "string",
                    "description": "ID of the Monday.com item to get updates for.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of updates to retrieve. Default is 25.",
                },
            },
            "required": ["itemId"],
        },
    ),
    types.Tool(
        name=ToolName.GET_DOCS,
        description="Get a list of documents from Monday.com, optionally filtered by folder",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of documents to retrieve. Default is 25.",
                },
                "folder_id": {
                    "type": "string",
                    "description": "Optional folder ID to filter documents by.",
                },
            },
        },
    ),
    types.Tool(
        name=ToolName.GET_DOC_CONTENT,
        description="Get the content of a specific document by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "ID of the Monday.com document to retrieve.",
                },
            },
            "required": ["doc_id"],
        },
    ),
    types.Tool(
        name=ToolName.CREATE_DOC,
        description="Create a new document in Monday.com",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the document to create.",
                },
                "content": {
                    "type": "string",
                    "description": "Content of the document to create.",
                },
                "folder_id": {
                    "type": "string",
                    "description": "Optional folder ID to create the document in.",
                },
            },
            "required": ["title", "content"],
        },
    ),
    types.Tool(
        name=ToolName.ADD_DOC_BLOCK,
        description="Add a block to a document",
        inputSchema={
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "ID of the Monday.com document to add a block to.",
                },
                "block_type": {
                    "type": "string",
                    "description": "Type of block to add (normal_text, bullet_list, numbered_list, heading, divider, etc.).",
                },
                "content": {
                    "type": "string",
                    "description": "Content of the block to add.",
                },
                "after_block_id": {
                    "type": "string",
                    "description": "Optional ID of the block to add this block after.",
                },
            },
            "required": ["doc_id", "block_type", "content"],
        },
    ),
    types.Tool(
        name=ToolName.GET_ITEM_FILES,
        description="Get files (PDFs, documents, images, etc.) attached to a Monday.com item",
        inputSchema={
            "type": "object",
            "properties": {
                "itemId": {
                    "type": "string",
                    "description": "ID of the Monday.com item to get files from.",
                },
            },
            "required": ["itemId"],
        },
    ),
    types.Tool(
        name=ToolName.GET_UPDATE_FILES,
        description="Get files (PDFs, documents, images, etc.) attached to a specific update in Monday.com",
        inputSchema={
            "type": "object",
            "properties": {
                "updateId": {
                    "type": "string",
                    "description": "ID of the Monday.com update to get files from.",
                },
            },
            "required": ["updateId"],
        },
    ),
]


def register_tools(server: Server, monday_client: MondayClient) -> None:
    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return ServerTools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> Sequence[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        try:
            match name:
                case ToolName.CREATE_ITEM:
                    return await handle_monday_create_item(
                        boardId=arguments.get("boardId"),
                        itemTitle=arguments.get("itemTitle"),
                        groupId=arguments.get("groupId"),
                        parentItemId=arguments.get("parentItemId"),
                        columnValues=arguments.get("columnValues"),
                        monday_client=monday_client,
                    )
                case ToolName.GET_BOARD_COLUMNS:
                    return await handle_monday_get_board_columns(
                        boardId=arguments.get("boardId"), monday_client=monday_client
                    )
                case ToolName.GET_BOARD_GROUPS:
                    return await handle_monday_get_board_groups(
                        boardId=arguments.get("boardId"), monday_client=monday_client
                    )

                case ToolName.CREATE_UPDATE:
                    return await handle_monday_create_update_on_item(
                        itemId=arguments.get("itemId"),
                        updateText=arguments.get("updateText"),
                        monday_client=monday_client,
                    )

                case ToolName.UPDATE_ITEM:
                    return await handle_monday_update_item(
                        boardId=arguments.get("boardId"),
                        itemId=arguments.get("itemId"),
                        columnValues=arguments.get("columnValues"),
                        monday_client=monday_client,
                    )

                case ToolName.LIST_BOARDS:
                    return await handle_monday_list_boards(monday_client=monday_client)

                case ToolName.LIST_ITEMS_IN_GROUPS:
                    return await handle_monday_list_items_in_groups(
                        boardId=arguments.get("boardId"),
                        groupIds=arguments.get("groupIds"),
                        limit=arguments.get("limit"),
                        cursor=arguments.get("cursor"),
                        monday_client=monday_client,
                    )

                case ToolName.LIST_SUBITEMS_IN_ITEMS:
                    return await handle_monday_list_subitems_in_items(
                        itemIds=arguments.get("itemIds"), monday_client=monday_client
                    )

                case ToolName.GET_ITEM_UPDATES:
                    return await handle_monday_get_item_updates(
                        itemId=arguments.get("itemId"),
                        limit=arguments.get("limit", 25),
                        monday_client=monday_client,
                    )

                case ToolName.GET_DOCS:
                    return await handle_monday_get_docs(
                        limit=arguments.get("limit", 25),
                        folder_id=arguments.get("folder_id"),
                        monday_client=monday_client,
                    )

                case ToolName.GET_DOC_CONTENT:
                    return await handle_monday_get_doc_content(
                        doc_id=arguments.get("doc_id"),
                        monday_client=monday_client,
                    )

                case ToolName.CREATE_DOC:
                    return await handle_monday_create_doc(
                        title=arguments.get("title"),
                        content=arguments.get("content"),
                        folder_id=arguments.get("folder_id"),
                        monday_client=monday_client,
                    )

                case ToolName.ADD_DOC_BLOCK:
                    return await handle_monday_add_doc_block(
                        doc_id=arguments.get("doc_id"),
                        block_type=arguments.get("block_type"),
                        content=arguments.get("content"),
                        after_block_id=arguments.get("after_block_id"),
                        monday_client=monday_client,
                    )

                case ToolName.GET_ITEM_FILES:
                    return await handle_monday_get_item_files(
                        itemId=arguments.get("itemId"),
                        monday_client=monday_client,
                    )
                
                case ToolName.GET_UPDATE_FILES:
                    return await handle_monday_get_update_files(
                        updateId=arguments.get("updateId"),
                        monday_client=monday_client,
                    )

                case _:
                    raise ValueError(f"Undefined behaviour for tool: {name}")

        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            raise
